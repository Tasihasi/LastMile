"""The address pipeline: cache -> raw geocode -> rule-based parser + re-geocode -> Google -> review queue.

Every stage works in batches of ``GEOCODE_CONCURRENCY`` (default 5) requests in parallel. Worker threads only
call the geocoder; all database work happens in the calling thread. ``run`` is a generator that yields each stop
as soon as it is final, so the NDJSON progress stream keeps its shape.

Stages recorded in ``DeliveryStop.geocode_stage``: cache, raw, parsed, google, manual.
"""

import logging
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from django.conf import settings

from . import consistency
from .addressparse import ParseResult, parse_address
from .districts import extract_postal_code
from .geocoder import GeocodeError, GeocodeQuery, GeocodeResult, google_provider, primary_provider
from .models import DeliveryStop

logger = logging.getLogger(__name__)

NOT_FOUND = "Address not found"
MAX_CANDIDATES = 5


@dataclass
class _Unit:
    """One distinct raw address; every stop with the same text shares its outcome."""

    raw: str
    stops: list
    zip: str
    parse: ParseResult | None = None
    error: str = ""
    rejected: str = ""
    tried: set = field(default_factory=set)


def _batches(items: list, size: int) -> Iterator[list]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _call(provider, query: GeocodeQuery) -> tuple[GeocodeResult | None, str]:
    """Never raises: one bad address must not abort its batch."""
    try:
        return provider.geocode(query), ""
    except GeocodeError as e:
        return None, str(e)
    except Exception as e:  # noqa: BLE001 - provider bugs/timeouts must not kill the run
        logger.exception("geocoder provider crashed for %r", query.text)
        return None, f"{type(e).__name__}: {e}"


def _run_batches(ex, jobs: list, size: int) -> Iterator[tuple]:
    """jobs: (unit, query, provider, zip, city). Yields (unit, query, zip, city, result, error) as each finishes."""
    for chunk in _batches(jobs, size):
        futures = {
            ex.submit(_call, provider, query): (unit, query, zp, city) for unit, query, provider, zp, city in chunk
        }
        for fut in as_completed(futures):
            unit, query, zp, city = futures[fut]
            result, error = fut.result()
            yield unit, query, zp, city, result, error


def _accept(unit: _Unit, result: GeocodeResult | None, error: str, zp: str, city: str) -> bool:
    """Record the outcome on the unit; True when the hit exists and agrees with the zip/settlement."""
    if error:
        unit.error = error
    if result is None:
        return False
    ok, reason = consistency.check(result.lat, result.lng, zp, city)
    if not ok:
        unit.rejected = reason
        return False
    return True


def _apply_parse(stop, unit: _Unit) -> None:
    parse = unit.parse
    if parse is None:
        return
    stop.cleaned_address = parse.cleaned[:500]
    stop.parsed_parts = {
        **parse.parts,
        "removed": parse.removed,
        "steps": parse.steps,
        "confidence": round(parse.confidence, 2),
    }
    if not stop.postal_code and parse.parts.get("zip"):
        stop.postal_code = parse.parts["zip"]


def _succeed(unit: _Unit, result: GeocodeResult, stage: str) -> Iterator[DeliveryStop]:
    for stop in unit.stops:
        stop.lat, stop.lng = result.lat, result.lng
        stop.geocode_status = "success"
        stop.geocode_error = ""
        stop.geocode_stage = stage
        stop.address_candidates = []
        _apply_parse(stop, unit)
        stop.save()
        yield stop


def _fail(unit: _Unit) -> Iterator[DeliveryStop]:
    if unit.error:
        message = f"Geocoder error: {unit.error}"[:500]
    elif unit.rejected:
        message = f"{NOT_FOUND} (the closest match was {unit.rejected})"
    else:
        message = NOT_FOUND
    candidates = []
    if unit.parse:
        candidates = [c for c in unit.parse.candidates() if c.lower() != unit.raw.lower()][:MAX_CANDIDATES]
    for stop in unit.stops:
        stop.geocode_status = "failed"
        stop.geocode_error = message
        stop.geocode_stage = "manual"
        stop.address_candidates = candidates
        _apply_parse(stop, unit)
        stop.save()
        yield stop


def _cached(raws: list[str]) -> dict[str, tuple[float, float]]:
    """Coordinates of identical addresses geocoded before (any session); the newest wins."""
    found: dict[str, tuple[float, float]] = {}
    for chunk in _batches(raws, 400):
        rows = DeliveryStop.objects.filter(
            raw_address__in=chunk, geocode_status="success", lat__isnull=False, lng__isnull=False
        ).order_by("id")
        for raw, lat, lng in rows.values_list("raw_address", "lat", "lng"):
            found[raw.strip()] = (lat, lng)
    return found


def run(
    stops: list[DeliveryStop], *, human_input: bool = False, concurrency: int | None = None
) -> Iterator[DeliveryStop]:
    """Geocode ``stops`` through all stages, yielding each saved stop when it is final.

    ``human_input``: the address was just typed by the planner (skip the cache, label a raw hit "manual").
    """
    size = max(1, concurrency or getattr(settings, "GEOCODE_CONCURRENCY", 5))
    units: dict[str, _Unit] = {}
    for stop in stops:
        raw = (stop.raw_address or "").strip()
        unit = units.setdefault(raw, _Unit(raw=raw, stops=[], zip=extract_postal_code(raw)))
        unit.stops.append(stop)

    todo: list[_Unit] = []
    for raw, unit in units.items():
        if not raw:
            for stop in unit.stops:
                stop.geocode_status, stop.geocode_error, stop.geocode_stage = "failed", "Address is empty", "manual"
                stop.save()
                yield stop
        else:
            todo.append(unit)

    # Stage 0: identical addresses geocoded before.
    if todo and not human_input:
        cache = _cached([u.raw for u in todo])
        rest = []
        for unit in todo:
            hit = cache.get(unit.raw)
            if hit and consistency.check(hit[0], hit[1], unit.zip)[0]:
                yield from _succeed(unit, GeocodeResult(hit[0], hit[1]), "cache")
            else:
                rest.append(unit)
        todo = rest
    if not todo:
        return

    provider = primary_provider()
    with ThreadPoolExecutor(max_workers=size) as ex:
        # Stage 1: the address as typed.
        pending: list[_Unit] = []
        jobs = [(u, GeocodeQuery(text=u.raw, postalcode=""), provider, u.zip, "") for u in todo]
        for unit, query, zp, city, result, error in _run_batches(ex, jobs, size):
            unit.tried.add(query.text.lower())
            if _accept(unit, result, error, zp, city):
                yield from _succeed(unit, result, "manual" if human_input else "raw")
            else:
                pending.append(unit)

        # Stage 2: rule-based parser on the failures, then the same batches with the cleaned variants.
        for unit in pending:
            unit.parse = parse_address(unit.raw)
        rounds = max((len([v for v in u.parse.variants if v.auto_accept]) for u in pending), default=0)
        for _round in range(rounds):
            jobs = []
            for unit in pending:
                variants = [v for v in unit.parse.variants if v.auto_accept and v.query.lower() not in unit.tried]
                if variants:
                    v = variants[0]
                    unit.tried.add(v.query.lower())
                    p = v.params
                    query = GeocodeQuery(
                        text=v.query,
                        street=p.get("street", ""),
                        city=p.get("city", ""),
                        postalcode=p.get("postalcode", ""),
                    )
                    jobs.append((unit, query, provider, unit.parse.parts["zip"], unit.parse.parts["city"]))
            resolved = set()
            for unit, _query, zp, city, result, error in _run_batches(ex, jobs, size):
                if _accept(unit, result, error, zp, city):
                    resolved.add(id(unit))
                    yield from _succeed(unit, result, "parsed")
            pending = [u for u in pending if id(u) not in resolved]

        # Stage 3: Google, only for what is still unresolved and only when a key is configured.
        google = google_provider()
        if google and pending:
            jobs = []
            for unit in pending:
                parts = unit.parse.parts if unit.parse else {"zip": unit.zip, "city": ""}
                text = (unit.parse.cleaned if unit.parse and unit.parse.cleaned else unit.raw) or unit.raw
                jobs.append(
                    (
                        unit,
                        GeocodeQuery(text=text, postalcode=parts["zip"], city=parts["city"]),
                        google,
                        parts["zip"],
                        parts["city"],
                    )
                )
            resolved = set()
            for unit, _query, zp, city, result, error in _run_batches(ex, jobs, size):
                if _accept(unit, result, error, zp, city):
                    resolved.add(id(unit))
                    yield from _succeed(unit, result, "google")
            pending = [u for u in pending if id(u) not in resolved]

    # Stage 4: the review queue.
    for unit in pending:
        yield from _fail(unit)


def geocode_stop(stop: DeliveryStop, *, human_input: bool = False) -> DeliveryStop:
    """Run the whole pipeline for one stop (used when the planner retypes an address)."""
    for done in run([stop], human_input=human_input):
        stop = done
    return stop
