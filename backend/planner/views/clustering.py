from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .. import zones
from ..clustering import calculate_n_clusters, cluster_zip_atomic, find_zip_conflicts, split_counts, stop_zip
from ..districts import district_label, extract_district, extract_zip
from ..models import DeliverySession, DeliveryStop
from ..zone_allocation import allocate_zones
from ..zone_splitting import resolve_unassigned
from .helpers import require_planner


def _parse_assignments(raw):
    """Validate the split-planner assignments payload.

    Each item: {"biker_id": int|null, "target_stops": int, "district": int|null, "zip": int|null}.
    A "zip" lock (exact irányítószám) takes priority over a "district" lock when both are set.
    Returns (parsed_list, error_message).
    """
    if not isinstance(raw, list) or not raw:
        return None, "assignments must be a non-empty list."

    parsed = []
    for item in raw:
        if not isinstance(item, dict):
            return None, "Each assignment must be an object."

        owner = None
        biker_id = item.get("biker_id")
        if biker_id is not None:
            try:
                owner = User.objects.get(id=int(biker_id), profile__role="biker")
            except (User.DoesNotExist, ValueError, TypeError):
                return None, f"Biker {biker_id} not found."

        try:
            target = max(int(item.get("target_stops") or 0), 0)
        except (ValueError, TypeError):
            return None, "target_stops must be a number."

        district = item.get("district")
        if district is not None:
            try:
                district = int(district)
            except (ValueError, TypeError):
                return None, "district must be a number."
            if not 1 <= district <= 23:
                return None, "district must be between 1 and 23."

        zip_code = item.get("zip")
        if zip_code is not None:
            try:
                zip_code = int(zip_code)
            except (ValueError, TypeError):
                return None, "zip must be a number."
            if extract_district(str(zip_code)) is None:
                return None, "zip must be a valid Budapest irányítószám."

        window = item.get("window_minutes")
        if window is not None:
            try:
                window = float(window)
            except (ValueError, TypeError):
                return None, "window_minutes must be a number."
            if window <= 0:
                return None, "window_minutes must be positive."
        multiplier = item.get("multiplier")
        if multiplier is not None:
            try:
                multiplier = float(multiplier)
            except (ValueError, TypeError):
                return None, "multiplier must be a number."
            if multiplier <= 0:
                return None, "multiplier must be positive."

        parsed.append(
            {
                "owner": owner,
                "target_stops": target,
                "district": district,
                "zip": zip_code,
                "window_minutes": window,
                "multiplier": multiplier,
            }
        )
    with_window = [a for a in parsed if a["window_minutes"] is not None]
    if with_window:
        if len(with_window) != len(parsed):
            return None, "window_minutes must be given for every biker or for none."
        if any(a["zip"] is not None or a["district"] is not None for a in parsed):
            return None, "window_minutes cannot be combined with a zip/district lock."
    return parsed, None


def _build_assignment_clusters(geocoded_stops, assignments, max_stops=48):
    """Distribute stops across assignments honouring area locks and targets.

    An assignment can be locked to an exact irányítószám ("zip", the
    fine-grained key) or, when no zip is set, to a whole district (the
    coarse fallback). Zip locks are applied first so they always win over a
    district lock. A postal code is never split: every stop of a zip ends up
    in the same cluster.

    Returns (clusters, leftover, oversized_zips, unzipped_stops). clusters is
    index-aligned with assignments; leftover holds stops no assignment can take
    (only when every assignment is area-locked).
    """
    pool = list(geocoded_stops)
    clusters = [[] for _ in assignments]
    oversized = []
    unzipped = []

    # Area locks: zip locks first, then district locks.
    area_groups = {}
    for i, a in enumerate(assignments):
        if a["zip"] is not None:
            area_groups.setdefault(("zip", str(a["zip"])), []).append(i)
    for i, a in enumerate(assignments):
        if a["zip"] is None and a["district"] is not None:
            area_groups.setdefault(("district", a["district"]), []).append(i)

    for (kind, value), idxs in area_groups.items():
        if kind == "zip":

            def matches(stop, value=value):
                return stop_zip(stop) == value
        else:

            def matches(stop, value=value):
                return extract_district(stop_zip(stop)) == value

        area_stops = [s for s in pool if matches(s)]
        pool = [s for s in pool if not matches(s)]
        if len(idxs) == 1:
            clusters[idxs[0]] = area_stops
        elif kind == "zip":
            # One zip, several bikers: the zip is indivisible, the first biker takes it all.
            clusters[idxs[0]] = area_stops
        else:
            result = cluster_zip_atomic(
                area_stops,
                targets=split_counts(len(area_stops), [assignments[i]["target_stops"] for i in idxs]),
                max_stops=max_stops,
            )
            for i, group in zip(idxs, result.clusters, strict=True):
                clusters[i] = group
            oversized += result.oversized_zips
            unzipped += result.unzipped_stops

    free_idxs = [i for i, a in enumerate(assignments) if a["zip"] is None and a["district"] is None]
    if not free_idxs:
        return clusters, pool, oversized, unzipped

    counts = split_counts(len(pool), [assignments[i]["target_stops"] for i in free_idxs])
    result = cluster_zip_atomic(pool, targets=counts, max_stops=max_stops)
    for i, group in zip(free_idxs, result.clusters, strict=True):
        clusters[i] = group
    return clusters, [], oversized + result.oversized_zips, unzipped + result.unzipped_stops


def _build_zone_first_clusters(geocoded_stops, assignments):
    """A5: whole zones onto bikers by time window; leftovers stay zip-atomic (A2 behaviour).

    Returns (clusters, route_info, unassigned_zones, unzipped_stops), index-aligned with assignments.
    """
    bikers = [
        {"id": i, "window_minutes": a["window_minutes"], "multiplier": a["multiplier"] or 1.0}
        for i, a in enumerate(assignments)
    ]
    alloc = allocate_zones(geocoded_stops, bikers)
    # A6: zones that fit whole nowhere are broken up zip by zip, as few as possible.
    resolved = resolve_unassigned(alloc, bikers)
    n = len(assignments)
    clusters = [list(resolved["routes"][i]["stops"]) for i in range(n)]

    unzipped = [s for s in geocoded_stops if not stop_zip(s)]
    if unzipped:
        smallest = min(range(n), key=lambda i: (len(clusters[i]), i))
        clusters[smallest] += unzipped

    over = set(resolved["over_capacity_routes"])
    overrun = set(resolved["overrun_routes"])
    info = [
        {
            "load_minutes": resolved["routes"][i]["load_minutes"],
            "capacity_minutes": resolved["routes"][i]["capacity_minutes"],
            "zones": alloc["routes"][i]["zones"],
            "over_capacity": i in over,
            "uses_overrun": i in overrun,
        }
        for i in range(n)
    ]
    extras = {
        "split_exact": resolved["exact"],
        "split_zones": resolved["split_zones"],  # parts[].route is an assignment index until names exist
        "over_capacity_zips": resolved["over_capacity_zips"],
    }
    return clusters, info, alloc["unassigned_zones"], unzipped, extras


@api_view(["POST"])
@transaction.atomic
def cluster_session(request, session_id):
    """Split a large session into clustered sub-routes using KMeans."""
    if not require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    # Lock the session row to prevent concurrent clustering of the same session
    try:
        session = DeliverySession.objects.select_for_update().get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    if session.sub_routes.exists():
        return Response(
            {"error": "Session already has sub-routes. Delete them first to re-cluster."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if session.status in (DeliverySession.Status.IN_PROGRESS, DeliverySession.Status.FINISHED):
        return Response(
            {"error": "Cannot split a route that is in progress or finished."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # A sub-route can itself be split further (e.g. it's still too large, or
    # the planner wants to divide it among more bikers) -- session.parent
    # being set just means the new children nest one level deeper.

    geocoded_stops = list(
        session.stops.filter(
            geocode_status__in=["success", "skipped"], lat__isnull=False, lng__isnull=False, excluded=False
        )
    )
    skipped_count = session.stops.filter(excluded=False).exclude(geocode_status__in=["success", "skipped"]).count()

    if len(geocoded_stops) < 2:
        return Response(
            {"error": "Need at least 2 geocoded stops to cluster."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    route_info, unassigned_zones, zone_extras = None, [], {"split_zones": [], "over_capacity_zips": []}
    unused_bikers = []
    assignments_raw = request.data.get("assignments")
    if assignments_raw is not None:
        assignments, err = _parse_assignments(assignments_raw)
        if err:
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)
        max_stops = int(request.data.get("max_stops_per_route", 48))
        zone_first = all(
            a["window_minutes"] is not None and a["zip"] is None and a["district"] is None for a in assignments
        )
        if zone_first:
            clusters, route_info, unassigned_zones, unzipped, zone_extras = _build_zone_first_clusters(
                geocoded_stops, assignments
            )
            leftover, oversized_zips = [], []
            # A biker the time windows don't need gets no (empty) route.
            used = [i for i, c in enumerate(clusters) if c]
            if len(used) < len(clusters):
                position = {old: new for new, old in enumerate(used)}
                for z in zone_extras["split_zones"]:
                    for part in z["parts"]:
                        part["route"] = position[part["route"]]
                unused_bikers = [
                    assignments[i]["owner"].username if assignments[i]["owner"] else None
                    for i in range(len(clusters))
                    if i not in position
                ]
                clusters = [clusters[i] for i in used]
                route_info = [route_info[i] for i in used]
                assignments = [assignments[i] for i in used]
            by_zip = {}
            for c in clusters:
                for st in c:
                    by_zip[stop_zip(st)] = by_zip.get(stop_zip(st), 0) + 1
            oversized_zips = [{"zip": z, "stop_count": n} for z, n in sorted(by_zip.items()) if z and n > max_stops]
        else:
            clusters, leftover, oversized_zips, unzipped = _build_assignment_clusters(
                geocoded_stops, assignments, max_stops=max_stops
            )
        owners = [a["owner"] for a in assignments]
        if leftover:
            # Every assignment was district-locked; keep the rest reviewable.
            clusters.append(leftover)
            owners.append(None)
    else:
        max_stops = int(request.data.get("max_stops_per_route", 48))
        n_routes_param = request.data.get("n_routes")
        n_routes = (
            int(n_routes_param) if n_routes_param is not None else calculate_n_clusters(len(geocoded_stops), max_stops)
        )
        result = cluster_zip_atomic(geocoded_stops, n_routes=n_routes, max_stops=max_stops)
        clusters = [c for c in result.clusters if c]
        oversized_zips, unzipped = result.oversized_zips, result.unzipped_stops
        owners = [None] * len(clusters)

    sub_routes = []
    for i, (cluster, owner) in enumerate(zip(clusters, owners, strict=True), start=1):
        child = DeliverySession.objects.create(
            parent=session,
            owner=owner,
            name=f"{(session.name or 'Route')[:248]}_{i}",
            original_file=session.original_file,
        )

        child_stops = []
        for stop in cluster:
            child_stops.append(
                DeliveryStop(
                    session=child,
                    name=stop.name,
                    raw_address=stop.raw_address,
                    product_code=stop.product_code,
                    recipient_name=stop.recipient_name,
                    recipient_phone=stop.recipient_phone,
                    lat=stop.lat,
                    lng=stop.lng,
                    geocode_status=stop.geocode_status,
                    geocode_error=stop.geocode_error,
                    postal_code=stop.postal_code,
                )
            )
        DeliveryStop.objects.bulk_create(child_stops)

        sub_routes.append(
            {
                "id": str(child.id),
                "name": child.name,
                "stop_count": len(cluster),
                "owner_id": owner.id if owner else None,
                "owner_name": owner.username if owner else None,
                **(route_info[i - 1] if route_info and i <= len(route_info) else {}),
            }
        )

    names = [r["name"] for r in sub_routes]
    split_zones = [
        {
            "zone_id": z["zone_id"],
            "parts": [{"zips": p["zips"], "route": names[p["route"]]} for p in z["parts"]],
        }
        for z in zone_extras["split_zones"]
    ]

    session.status = DeliverySession.Status.SPLIT
    session.save(update_fields=["status"])

    stop_counts = [len(c) for c in clusters]
    return Response(
        {
            "parent_id": str(session.id),
            "sub_routes": sub_routes,
            "oversized_zips": oversized_zips,
            "unassigned_zones": unassigned_zones,
            "split_zones": split_zones,
            "over_capacity_zips": zone_extras["over_capacity_zips"],
            "unused_bikers": unused_bikers,
            "split_exact": zone_extras.get("split_exact", True),
            "zip_conflicts": find_zip_conflicts(list(session.sub_routes.all())),
            "unzipped_stop_ids": [s.id for s in unzipped],
            "cluster_summary": {
                "total_stops": len(geocoded_stops),
                "skipped_stops": skipped_count,
                "n_routes": len(clusters),
                "avg_stops_per_route": round(len(geocoded_stops) / len(clusters), 1),
                "min_stops": min(stop_counts),
                "max_stops": max(stop_counts),
            },
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@transaction.atomic
def move_stop(request, session_id):
    """Move a stop from one sub-route to a sibling sub-route."""
    if not require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        source_session = DeliverySession.objects.select_for_update().get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    stop_id = request.data.get("stop_id")
    to_session_id = request.data.get("to_session_id")

    if not stop_id or not to_session_id:
        return Response(
            {"error": "stop_id and to_session_id are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        stop = source_session.stops.get(id=int(stop_id))
    except (DeliveryStop.DoesNotExist, ValueError, TypeError):
        return Response({"error": "Stop not found in this session."}, status=status.HTTP_404_NOT_FOUND)

    try:
        target_session = DeliverySession.objects.select_for_update().get(id=to_session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Target session not found."}, status=status.HTTP_404_NOT_FOUND)

    if source_session.parent_id is None or source_session.parent_id != target_session.parent_id:
        return Response(
            {"error": "Can only move stops between sibling sub-routes (same parent)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if source_session.status == DeliverySession.Status.IN_PROGRESS:
        return Response(
            {"error": "Cannot move stops from an in-progress route."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if target_session.status == DeliverySession.Status.IN_PROGRESS:
        return Response(
            {"error": "Cannot move stops to an in-progress route."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    stop.session = target_session
    stop.sequence_order = None
    stop.save(update_fields=["session_id", "sequence_order"])

    for s in [source_session, target_session]:
        s.route_geometry = None
        s.route_segments = None
        s.total_duration = None
        s.total_distance = None
        s.save(update_fields=["route_geometry", "route_segments", "total_duration", "total_distance"])

    return Response(
        {
            "stop_id": stop.id,
            "from_session_id": str(source_session.id),
            "to_session_id": str(target_session.id),
            "from_count": source_session.stops.count(),
            "to_count": target_session.stops.count(),
            "zip_conflicts": find_zip_conflicts(list(target_session.parent.sub_routes.all())),
        }
    )


@api_view(["POST"])
@transaction.atomic
def move_zip(request, session_id):
    """Move every stop of a postal code (or a whole zone) into one sub-route."""
    if not require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        parent = DeliverySession.objects.select_for_update().get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)
    if parent.status != DeliverySession.Status.SPLIT:
        return Response({"error": "Session is not split."}, status=status.HTTP_400_BAD_REQUEST)

    zip_code = str(request.data.get("zip") or "").strip()
    zone_id = str(request.data.get("zone_id") or "").strip()
    to_session_id = request.data.get("to_session_id")
    if bool(zip_code) == bool(zone_id):
        return Response({"error": "Send exactly one of zip or zone_id."}, status=status.HTTP_400_BAD_REQUEST)
    if not to_session_id:
        return Response({"error": "to_session_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    if zone_id:
        wanted = set(zones.zips_in_zone(zone_id))
        if not wanted:
            return Response({"error": f"Unknown zone {zone_id}."}, status=status.HTTP_400_BAD_REQUEST)
    else:
        wanted = {zip_code}

    children = {str(c.id): c for c in parent.sub_routes.select_for_update()}
    target = children.get(str(to_session_id))
    if target is None:
        return Response({"error": "Target is not a sub-route of this session."}, status=status.HTTP_404_NOT_FOUND)

    to_move = [
        s
        for child in children.values()
        for s in child.stops.filter(excluded=False)
        if stop_zip(s) in wanted and child.id != target.id
    ]
    present = {stop_zip(s) for s in to_move}
    if not zone_id and not present and not target.stops.filter(postal_code=zip_code).exists():
        return Response({"error": f"No stops with postal code {zip_code}."}, status=status.HTTP_400_BAD_REQUEST)

    blocked = {"in_progress", "finished"}
    touched = {s.session_id for s in to_move}
    for sid in touched | ({target.id} if to_move else set()):
        child = next(c for c in children.values() if c.id == sid)
        if child.status in blocked:
            return Response(
                {"error": f"Cannot move stops: route {child.name} is {child.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    for stop in to_move:
        stop.session = target
        stop.sequence_order = None
        stop.save(update_fields=["session_id", "sequence_order"])

    for sid in touched | ({target.id} if to_move else set()):
        child = next(c for c in children.values() if c.id == sid)
        child.route_geometry = None
        child.route_segments = None
        child.total_duration = None
        child.total_distance = None
        child.save(update_fields=["route_geometry", "route_segments", "total_duration", "total_distance"])

    routes = list(parent.sub_routes.all())
    return Response(
        {
            "moved_count": len(to_move),
            "moved_zips": sorted(z for z in present if z),
            "to_session_id": str(target.id),
            "counts": {str(r.id): r.stops.count() for r in routes},
            "zip_conflicts": find_zip_conflicts(routes),
        }
    )


@api_view(["DELETE"])
@transaction.atomic
def uncluster_session(request, session_id):
    """Undo a split: delete all sub-routes and reset parent to not_started."""
    if not require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        session = DeliverySession.objects.select_for_update().get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    if session.status != DeliverySession.Status.SPLIT:
        return Response(
            {"error": "Session is not split."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if session.sub_routes.filter(status=DeliverySession.Status.IN_PROGRESS).exists():
        return Response(
            {"error": "Cannot undo split while a sub-route is in progress."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    deleted_count = session.sub_routes.count()
    session.sub_routes.all().delete()
    session.status = DeliverySession.Status.NOT_STARTED
    session.save(update_fields=["status"])

    return Response({"parent_id": str(session.id), "deleted_routes": deleted_count})


@api_view(["GET"])
def session_districts(request, session_id):
    """City districts present in a session's geocoded stops, for the split planner."""
    if not require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        session = DeliverySession.objects.get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    stops = session.stops.filter(geocode_status__in=["success", "skipped"], lat__isnull=False, lng__isnull=False).only(
        "raw_address"
    )

    counts = {}
    zip_counts_by_district = {}
    unknown = 0
    total = 0
    for stop in stops:
        total += 1
        district = extract_district(stop.raw_address)
        if district is None:
            unknown += 1
            continue
        counts[district] = counts.get(district, 0) + 1
        zip_code = extract_zip(stop.raw_address)
        by_zip = zip_counts_by_district.setdefault(district, {})
        by_zip[zip_code] = by_zip.get(zip_code, 0) + 1

    # Lock options for the split planner: primarily by exact irányítószám,
    # falling back to the whole district when its stops share a single zip.
    areas = []
    for district, stop_count in sorted(counts.items()):
        by_zip = zip_counts_by_district[district]
        if len(by_zip) <= 1:
            areas.append(
                {
                    "type": "district",
                    "district": district,
                    "zip": None,
                    "label": district_label(district),
                    "stop_count": stop_count,
                }
            )
        else:
            for zip_code, zip_count in sorted(by_zip.items()):
                areas.append(
                    {
                        "type": "zip",
                        "district": district,
                        "zip": zip_code,
                        "label": f"{district_label(district)} – {zip_code}",
                        "stop_count": zip_count,
                    }
                )

    return Response(
        {
            "districts": [
                {"district": d, "label": district_label(d), "stop_count": c} for d, c in sorted(counts.items())
            ],
            "areas": areas,
            "unknown_district_stops": unknown,
            "total_stops": total,
        }
    )


@api_view(["DELETE"])
@transaction.atomic
def remove_stop(request, session_id, stop_id):
    """Remove a single stop from a route during split review."""
    if not require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        session = DeliverySession.objects.select_for_update().get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    if session.status == DeliverySession.Status.IN_PROGRESS:
        return Response(
            {"error": "Cannot remove stops from an in-progress route."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        stop = session.stops.get(id=stop_id)
    except DeliveryStop.DoesNotExist:
        return Response({"error": "Stop not found in this session."}, status=status.HTTP_404_NOT_FOUND)

    stop.delete()

    session.route_geometry = None
    session.route_segments = None
    session.total_duration = None
    session.total_distance = None
    session.save(update_fields=["route_geometry", "route_segments", "total_duration", "total_distance"])

    return Response({"removed_stop_id": stop_id, "remaining_stops": session.stops.count()})
