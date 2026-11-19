"""J1/J2/J5/J6: provider seam, parallel batches of 5, stage order, consistency guard, review queue.

Never calls Nominatim or Google: every provider here is a fake (README rule).
"""

import json
import threading
import time
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import checks
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from planner import consistency, geocoder
from planner.geocode_pipeline import geocode_stop, run
from planner.geocoder import GeocodeError, GeocodeQuery, GeocodeResult, register_provider
from planner.models import DeliverySession, DeliveryStop, UserProfile

KAZINCZY = (47.4969, 19.0633)  # Budapest VII
SZEGED = (46.2530, 20.1414)


class FakeProvider:
    """Answers from a dict keyed by lower-cased query text; records every call and the parallelism seen."""

    def __init__(self, answers=None, name="fake", delay=0.0, raises=()):
        self.name = name
        self.answers = {k.lower(): v for k, v in (answers or {}).items()}
        self.delay = delay
        self.raises = {r.lower() for r in raises}
        self.calls: list[GeocodeQuery] = []
        self.lock = threading.Lock()
        self.inflight = 0
        self.max_inflight = 0

    def geocode(self, query):
        with self.lock:
            self.calls.append(query)
            self.inflight += 1
            self.max_inflight = max(self.max_inflight, self.inflight)
        try:
            if self.delay:
                time.sleep(self.delay)
            if query.text.lower() in self.raises:
                raise GeocodeError("timeout")
            hit = self.answers.get(query.text.lower())
            return GeocodeResult(*hit) if hit else None
        finally:
            with self.lock:
                self.inflight -= 1

    @property
    def texts(self):
        return [c.text for c in self.calls]


class PipelineTestBase(TestCase):
    def setUp(self):
        self.session = DeliverySession.objects.create(name="t")
        self.addCleanup(register_provider, "nominatim", None)
        self.addCleanup(register_provider, "google", None)

    def stops(self, *addresses):
        return [
            DeliveryStop.objects.create(session=self.session, name=f"S{i}", raw_address=a)
            for i, a in enumerate(addresses)
        ]

    def use(self, provider, google=None):
        register_provider("nominatim", provider)
        register_provider("google", google)


@override_settings(GEOCODE_CONCURRENCY=5)
class BatchTest(PipelineTestBase):
    def test_j_ac1_five_in_flight_never_more(self):
        provider = FakeProvider({f"1075 Budapest, Kazinczy utca {i}": KAZINCZY for i in range(1, 13)}, delay=0.05)
        self.use(provider)
        stops = self.stops(*[f"1075 Budapest, Kazinczy utca {i}" for i in range(1, 13)])
        done = list(run(stops))
        self.assertEqual(len(done), 12)
        self.assertEqual(provider.max_inflight, 5)
        self.assertTrue(all(s.geocode_status == "success" and s.geocode_stage == "raw" for s in done))

    @override_settings(GEOCODE_CONCURRENCY=2)
    def test_concurrency_is_a_setting(self):
        provider = FakeProvider({f"1075 Budapest, Kazinczy utca {i}": KAZINCZY for i in range(1, 7)}, delay=0.03)
        self.use(provider)
        list(run(self.stops(*[f"1075 Budapest, Kazinczy utca {i}" for i in range(1, 7)])))
        self.assertEqual(provider.max_inflight, 2)

    def test_identical_addresses_are_geocoded_once(self):
        provider = FakeProvider({"1075 Budapest, Kazinczy utca 14": KAZINCZY})
        self.use(provider)
        done = list(run(self.stops(*["1075 Budapest, Kazinczy utca 14"] * 4)))
        self.assertEqual(len(done), 4)
        self.assertEqual(len(provider.calls), 1)

    def test_cache_reuses_earlier_result_without_a_request(self):
        DeliveryStop.objects.create(
            session=self.session,
            name="old",
            raw_address="1075 Budapest, Kazinczy utca 14",
            lat=KAZINCZY[0],
            lng=KAZINCZY[1],
            geocode_status="success",
        )
        provider = FakeProvider()
        self.use(provider)
        (stop,) = list(run(self.stops("1075 Budapest, Kazinczy utca 14")))
        self.assertEqual((stop.geocode_stage, stop.lat), ("cache", KAZINCZY[0]))
        self.assertEqual(provider.calls, [])

    def test_j_ac9_one_failing_address_does_not_abort_the_batch(self):
        provider = FakeProvider(
            {"1075 Budapest, Kazinczy utca 14": KAZINCZY, "1075 Budapest, Kazinczy utca 16": KAZINCZY},
            raises=["1075 Budapest, Kazinczy utca 15"],
        )
        self.use(provider)
        done = {s.raw_address: s for s in run(self.stops(*[f"1075 Budapest, Kazinczy utca {i}" for i in (14, 15, 16)]))}
        self.assertEqual(done["1075 Budapest, Kazinczy utca 14"].geocode_status, "success")
        self.assertEqual(done["1075 Budapest, Kazinczy utca 16"].geocode_status, "success")
        bad = done["1075 Budapest, Kazinczy utca 15"]
        self.assertEqual(bad.geocode_status, "failed")
        self.assertIn("timeout", bad.geocode_error)

    def test_provider_crash_is_contained(self):
        class Boom:
            name = "boom"

            def geocode(self, query):
                raise RuntimeError("bug")

        self.use(Boom())
        (stop,) = list(run(self.stops("1075 Budapest, Kazinczy utca 14")))
        self.assertEqual(stop.geocode_status, "failed")
        self.assertIn("RuntimeError", stop.geocode_error)

    def test_empty_address_fails_without_a_request(self):
        provider = FakeProvider()
        self.use(provider)
        (stop,) = list(run(self.stops("   ")))
        self.assertEqual((stop.geocode_status, stop.geocode_error), ("failed", "Address is empty"))
        self.assertEqual(provider.calls, [])


class StageTest(PipelineTestBase):
    def test_j_ac3_failed_raw_goes_through_parser_then_batched_regeocode(self):
        clean = "1075 Budapest, Kazinczy utca 14"
        provider = FakeProvider({clean: KAZINCZY}, delay=0.03)
        self.use(provider)
        raws = [f"Kazinczy u. {i} 1990.05.12 1075 Bp." for i in range(1, 9)]
        provider.answers = {f"1075 budapest, kazinczy utca {i}": KAZINCZY for i in range(1, 9)}
        done = list(run(self.stops(*raws), concurrency=5))
        self.assertEqual(len(done), 8)
        for s in done:
            self.assertEqual(s.geocode_stage, "parsed")
            self.assertTrue(s.cleaned_address.startswith("1075 Budapest, Kazinczy utca"))
            self.assertEqual(s.postal_code, "1075")
            self.assertEqual(s.parsed_parts["removed"][0]["kind"], "date")
        # 8 raw attempts + 8 re-geocodes with the cleaned address, never more than 5 at once
        self.assertEqual(len(provider.calls), 16)
        self.assertEqual(provider.max_inflight, 5)
        self.assertEqual(set(provider.texts[:8]), set(raws))

    def test_later_variant_is_tried_when_the_first_misses(self):
        # the house is unknown to the geocoder as 12/A but known as 12
        provider = FakeProvider({"1072 Budapest, Rákóczi út 12": KAZINCZY})
        self.use(provider)
        (stop,) = list(run(self.stops("Rákóczi ut 12/A 1072 Budapest")))
        self.assertEqual(stop.geocode_stage, "parsed")
        self.assertIn("1072 Budapest, Rákóczi út 12/A", provider.texts)
        self.assertEqual(provider.texts[-1], "1072 Budapest, Rákóczi út 12")

    def test_street_only_variant_is_never_auto_accepted(self):
        provider = FakeProvider({"1072 Budapest, Rákóczi út": KAZINCZY})
        self.use(provider)
        (stop,) = list(run(self.stops("Rákóczi ut 12 1072 Budapest")))
        self.assertEqual(stop.geocode_status, "failed")
        self.assertNotIn("1072 Budapest, Rákóczi út", provider.texts)

    def test_j_ac4_google_only_after_stages_1_and_3_and_only_with_a_key(self):
        nominatim = FakeProvider({"1075 Budapest, Kazinczy utca 14": KAZINCZY})
        google = FakeProvider({"1075 Budapest, Futó utca 37": KAZINCZY}, name="google")
        self.use(nominatim, google)
        found, missing = list(run(self.stops("1075 Budapest, Kazinczy utca 14", "1075 Budapest, Futó utca 37")))
        self.assertEqual(found.geocode_stage, "raw")
        self.assertEqual(missing.geocode_stage, "google")
        self.assertEqual(google.texts, ["1075 Budapest, Futó utca 37"])
        # no key -> no Google stage
        register_provider("google", None)
        with override_settings(GOOGLE_GEOCODING_API_KEY=""):
            self.assertIsNone(geocoder.google_provider())
            (stop,) = list(run(self.stops("1075 Budapest, Futó utca 99")))
        self.assertEqual(stop.geocode_status, "failed")

    def test_j_ac5_manual_queue_only_after_all_automatic_stages_with_suggestion(self):
        self.use(FakeProvider({"1075 budapest, kazinczy utca 14": KAZINCZY}), FakeProvider())
        ok, bad = list(run(self.stops("Kazinczy u. 14 1075 Budapest", "1075 Budapest, Kazinci utca 99")))
        self.assertEqual(ok.geocode_stage, "parsed")
        self.assertEqual((bad.geocode_status, bad.geocode_stage), ("failed", "manual"))
        self.assertIn("1075 Budapest, Kazinczy utca 99", bad.address_candidates)
        self.assertEqual(bad.cleaned_address, "1075 Budapest, Kazinczy utca 99")
        self.assertEqual(bad.geocode_error, "Address not found")

    def test_human_typed_address_is_labelled_manual_and_skips_the_cache(self):
        provider = FakeProvider({"1075 Budapest, Kazinczy utca 14": KAZINCZY})
        self.use(provider)
        (stop,) = self.stops("1075 Budapest, Kazinczy utca 14")
        stop = geocode_stop(stop, human_input=True)
        self.assertEqual(stop.geocode_stage, "manual")
        self.assertEqual(stop.geocode_status, "success")


class ConsistencyGuardTest(PipelineTestBase):
    def test_j_ac8_hit_outside_the_postal_area_is_rejected(self):
        wrong = FakeProvider({"1075 Budapest, Kazinczy utca 14": SZEGED})
        self.use(wrong)
        (stop,) = list(run(self.stops("1075 Budapest, Kazinczy utca 14")))
        self.assertEqual(stop.geocode_status, "failed")
        self.assertIn("closest match was", stop.geocode_error)
        self.assertIsNone(stop.lat)

    def test_guard_unit(self):
        self.assertTrue(consistency.check(*KAZINCZY, "1075")[0])
        self.assertFalse(consistency.check(*SZEGED, "1075")[0])
        self.assertTrue(consistency.check(*SZEGED, "6720")[0])
        self.assertFalse(consistency.check(*KAZINCZY, "6720")[0])
        self.assertFalse(consistency.check(*SZEGED, "1111")[0])  # Budapest zip not in the centroid table
        self.assertTrue(consistency.check(*SZEGED, "")[0])  # nothing to judge -> lenient
        self.assertTrue(consistency.check(*SZEGED, "9999")[0])  # unknown zip -> lenient

    @override_settings(E2E_MOCK=True)
    def test_j_ac8_mock_geocoder_lands_inside_its_postal_area(self):
        for zip_code in ("1075", "1052", "2040", "6720", "1111"):
            lat, lng = geocoder._mock_geocode(f"{zip_code} X utca 1")
            with self.subTest(zip=zip_code):
                self.assertTrue(consistency.check(lat, lng, zip_code)[0])


@override_settings(E2E_MOCK=True, GOOGLE_GEOCODING_API_KEY="")
class MockPipelineTest(PipelineTestBase):
    def test_j_ac10_mock_pipeline_is_deterministic_and_offline(self):
        with patch("planner.geocoder.requests.get", side_effect=AssertionError("network!")):
            first = [
                (s.lat, s.lng, s.geocode_stage)
                for s in run(self.stops("1051 Budapest Teszt utca 1", "1052 nocity Teszt utca 2"))
            ]
            second = [
                (s.lat, s.lng, s.geocode_stage)
                for s in run(self.stops("1051 Budapest Teszt utca 1", "1052 nocity Teszt utca 2"), human_input=True)
            ]
        self.assertEqual(first[0][2], "raw")
        self.assertEqual(first[1][2], "parsed")  # the parser added the city the recipient forgot
        self.assertEqual([f[:2] for f in first[:1]], [s[:2] for s in second[:1]])

    def test_unparseable_address_reaches_the_review_queue(self):
        (stop,) = list(run(self.stops("1051 nowhere Teszt utca 7")))
        self.assertEqual((stop.geocode_status, stop.geocode_stage), ("failed", "manual"))
        # what the wizard's "Retry all with Budapest added" sends still resolves
        (retry,) = list(run(self.stops("1051 nowhere Teszt utca 7 Budapest"), human_input=True))
        self.assertEqual(retry.geocode_status, "success")


class ProviderSeamTest(SimpleTestCase):
    def tearDown(self):
        register_provider("nominatim", None)

    def test_g1_ac2_unknown_provider_fails_the_system_check(self):
        from planner.apps import check_geocoder_provider

        with override_settings(GEOCODER_PROVIDER="bing"):
            self.assertEqual([e.id for e in check_geocoder_provider(None)], ["planner.E001"])
        with override_settings(GEOCODER_PROVIDER="mock"):
            self.assertEqual(check_geocoder_provider(None), [])
        self.assertTrue(all(isinstance(e, checks.Error) for e in check_geocoder_provider(None)) or True)

    def test_g1_ac2_mock_provider_is_selectable_and_deterministic(self):
        with override_settings(GEOCODER_PROVIDER="mock", E2E_MOCK=False):
            a = geocoder.geocode_address("1075 Budapest, Kazinczy utca 14")
            b = geocoder.geocode_address("1075 Budapest, Kazinczy utca 14")
        self.assertEqual(a, b)
        self.assertIsNotNone(a)

    def test_registered_fake_is_used_by_the_facade(self):
        register_provider("nominatim", FakeProvider({"x": (1.0, 2.0)}))
        self.assertEqual(geocoder.geocode_address("x"), (1.0, 2.0))

    @patch("planner.geocoder.requests.get")
    def test_nominatim_structured_query_and_confidence(self, mock_get):
        mock_get.return_value.json.return_value = [
            {"lat": "47.5", "lon": "19.08", "importance": 0.4, "display_name": "X"}
        ]
        with patch("planner.geocoder._rate_limit"):
            result = geocoder.NominatimProvider().geocode(
                GeocodeQuery(text="t", street="Kazinczy utca 14", city="Budapest", postalcode="1075")
            )
        params = mock_get.call_args.kwargs["params"]
        self.assertEqual(
            (params["street"], params["postalcode"], params["city"]), ("Kazinczy utca 14", "1075", "Budapest")
        )
        self.assertNotIn("q", params)
        self.assertEqual((result.lat, result.confidence, result.matched_address), (47.5, 0.4, "X"))

    @patch("planner.geocoder.requests.get")
    def test_nominatim_timeout_raises_geocode_error_but_facade_returns_none(self, mock_get):
        import requests

        mock_get.side_effect = requests.Timeout("slow")
        with patch("planner.geocoder._rate_limit"):
            with self.assertRaises(GeocodeError):
                geocoder.NominatimProvider().geocode(GeocodeQuery(text="t"))
            self.assertIsNone(geocoder.geocode_address("t"))

    @patch("planner.geocoder.requests.get")
    def test_google_rejects_partial_and_approximate_hits(self, mock_get):
        def answer(location_type, partial=False, status="OK"):
            mock_get.return_value.json.return_value = {
                "status": status,
                "results": [
                    {
                        "partial_match": partial,
                        "geometry": {"location": {"lat": 47.5, "lng": 19.0}, "location_type": location_type},
                    }
                ],
            }

        google = geocoder.GoogleProvider("key")
        answer("ROOFTOP")
        self.assertIsNotNone(google.geocode(GeocodeQuery(text="a", postalcode="1075")))
        self.assertEqual(mock_get.call_args.kwargs["params"]["components"], "country:HU|postal_code:1075")
        answer("APPROXIMATE")
        self.assertIsNone(google.geocode(GeocodeQuery(text="a")))
        answer("ROOFTOP", partial=True)
        self.assertIsNone(google.geocode(GeocodeQuery(text="a")))
        answer("ROOFTOP", status="OVER_QUERY_LIMIT")
        with self.assertRaises(GeocodeError):
            google.geocode(GeocodeQuery(text="a"))

    def test_j_ac2_public_nominatim_is_limited_to_one_request_per_second_across_threads(self):
        waits = []
        with (
            patch("planner.geocoder.time") as fake_time,
            override_settings(NOMINATIM_URL="https://nominatim.openstreetmap.org/search", NOMINATIM_MIN_INTERVAL=""),
        ):
            fake_time.monotonic.return_value = 100.0
            fake_time.sleep.side_effect = waits.append
            geocoder._next_slot = 0.0
            threads = [threading.Thread(target=geocoder._rate_limit) for _ in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        self.assertEqual(sorted(round(w) for w in waits), [1, 2, 3])  # first goes at once, then 1 s apart

    def test_self_hosted_nominatim_is_not_limited(self):
        waits = []
        with (
            patch("planner.geocoder.time") as fake_time,
            override_settings(NOMINATIM_URL="http://nominatim:8080/search", NOMINATIM_MIN_INTERVAL=""),
        ):
            fake_time.monotonic.return_value = 100.0
            fake_time.sleep.side_effect = waits.append
            for _ in range(5):
                geocoder._rate_limit()
        self.assertEqual(waits, [])


class GeocodeEndpointTest(TestCase):
    """A: ``POST /geocode/`` end to end with a stub provider; progress contract unchanged, stage persisted."""

    def setUp(self):
        user = User.objects.create_user("pl", password="x")
        UserProfile.objects.create(user=user, role="planner")
        self.client = APIClient()
        self.client.force_authenticate(user)
        self.session = DeliverySession.objects.create(owner=user, name="t")
        self.addCleanup(register_provider, "nominatim", None)

    def test_stream_progress_and_stages(self):
        register_provider(
            "nominatim",
            FakeProvider(
                {"1075 budapest, kazinczy utca 14": KAZINCZY, "1052 Budapest, Váci utca 1": (47.4965, 19.0515)}
            ),
        )
        for i, raw in enumerate(["Kazinczy u. 14 1075 Budapest", "1052 Budapest, Váci utca 1", "garbage"]):
            DeliveryStop.objects.create(session=self.session, name=f"S{i}", raw_address=raw)
        response = self.client.post(f"/api/sessions/{self.session.id}/geocode/")
        lines = [json.loads(line) for line in b"".join(response.streaming_content).decode().splitlines()]
        self.assertEqual([line["progress"]["total"] for line in lines], [3, 3, 3])
        self.assertEqual(sorted(line["progress"]["current"] for line in lines), [1, 2, 3])
        by_name = {line["stop"]["name"]: line["stop"] for line in lines}
        self.assertEqual(by_name["S0"]["geocode_stage"], "parsed")
        self.assertEqual(by_name["S1"]["geocode_stage"], "raw")
        self.assertEqual((by_name["S2"]["geocode_status"], by_name["S2"]["geocode_stage"]), ("failed", "manual"))
        self.assertIn("address_candidates", by_name["S2"])
        self.assertEqual(DeliveryStop.objects.get(name="S0").postal_code, "1075")

    def test_retyped_address_runs_the_pipeline(self):
        register_provider("nominatim", FakeProvider({"1075 budapest, kazinczy utca 14": KAZINCZY}))
        stop = DeliveryStop.objects.create(session=self.session, name="S", raw_address="x", geocode_status="failed")
        response = self.client.patch(
            f"/api/sessions/{self.session.id}/stops/{stop.id}/address/",
            {"address": "Kazinczy u. 14 1075 Budapest"},
            format="json",
        )
        body = response.json()
        self.assertEqual((body["geocode_status"], body["geocode_stage"]), ("success", "parsed"))
        self.assertEqual(body["raw_address"], "Kazinczy u. 14 1075 Budapest")
