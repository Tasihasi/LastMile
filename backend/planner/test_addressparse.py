"""J0/J3/J4: golden corpus and properties of the rule-based Hungarian address parser (no network, no AI)."""

from django.test import SimpleTestCase

from planner.addressparse import parse_address
from planner.addressparse.fold import damerau_levenshtein, phonetic
from planner.addressparse.housenumber import base_number, parse_house

# raw -> (zip, city, street, house). Hand-written messy cases, one behaviour each.
GOLDEN = [
    ("1075 Budapest, Kazinczy u. 14", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1075 Bp., Kazinczy u. 14", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("Kazinczy u. 14 1075 Budapest", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1075 Budapest Kazinczy utca 14.", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1075 BUDAPEST, KAZINCZY UTCA 14", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1075 budapest, kazinczy utca 14", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("H-1075 Budapest, Kazinczy utca 14", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1085 Budapest, Gyulai Pál u. 2", ("1085", "Budapest", "Gyulai Pál utca", "2")),
    ("1085 Budapest, Gyulai Pal u. 2", ("1085", "Budapest", "Gyulai Pál utca", "2")),
    ("1056 Budapest, Március 15. tér 7", ("1056", "Budapest", "Március 15. tér", "7")),
    ("1072 Budapest, Rákóczi út 12-14", ("1072", "Budapest", "Rákóczi út", "12-14")),
    ("1072 Budapest, Rákóczi ut 12/A", ("1072", "Budapest", "Rákóczi út", "12/A")),
    ("1072 Budapest, Rákóczi ut 12A", ("1072", "Budapest", "Rákóczi út", "12/A")),
    ("1075 Budapest, Károly krt. 3", ("1075", "Budapest", "Károly körút", "3")),
    ("1051 Budapest, Széchenyi rkp. 1", ("1051", "Budapest", "Széchenyi rakpart", "1")),
    ("1082 Budapest, Futó utca 37", ("1082", "Budapest", "Futó utca", "37")),
    ("1082 Budapest, Futó utca hrsz. 1234/5", ("1082", "Budapest", "Futó utca", "hrsz. 1234/5")),
    ("14 Kazinczy utca, 1075 Budapest", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1075 Budapest, Kazincyutca 14", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("2040 Budaörs, Fő u. 5", ("2040", "Budaörs", "Fő utca", "5")),
    ("2143 Kistarcsa, Fő utca 3", ("2143", "Kistarcsa", "Fő utca", "3")),
    ("6720 Szeged, Kossuth Lajos sgt. 9", ("6720", "Szeged", "Kossuth Lajos sugárút", "9")),
    ("4026 Debrecen Piac utca 20", ("4026", "Debrecen", "Piac utca", "20")),
    ("Budapest VII. ker. Kazinczy u. 14", ("", "Budapest", "Kazinczy utca", "14")),
    ("Budapest, 7. kerület, Kazinczy utca 14", ("", "Budapest", "Kazinczy utca", "14")),
    ("Bp. VII., Kazinczy utca 14", ("", "Budapest", "Kazinczy utca", "14")),
    ("Dr. Kovács János, 1075 Budapest, Kazinczy utca 14", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("Özv. Nagy Istvánné, Kazinczy utca 14, 1075 Budapest", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1075 Budapest, Kazinczy utca 14. 2. em. 5. ajtó", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1075 Budapest, Kazinczy utca 14 A lh. II. em. 5.", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1075 Budapest, Kazinczy utca 14, fszt. 3.", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1075   Budapest ,   Kazinczy   utca   14", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1075 Budapest; Kazinczy utca 14", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1075 Budapest | Kazinczy utca 14", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1075 Budapest,\nKazinczy utca 14", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1075 Budapest, Kazinczy utca 14 \U0001f600", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1051 nocity Teszt utca 5", ("1051", "Budapest", "Nocity Teszt utca", "5")),
    ("Kossuth Lajos u 5 1053 Budapest", ("1053", "Budapest", "Kossuth Lajos utca", "5")),
    ("1053 Budapest, Kossuth Lajos u. 5.", ("1053", "Budapest", "Kossuth Lajos utca", "5")),
    ("1075 Budapest, Kazinci utca 14", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1075 Budapest, Kazincy utca 14", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1073 Budapest, Erzsébet krt. 12", ("1073", "Budapest", "Erzsébet körút", "12")),
    ("1074 Budapest, Dohany utca 22", ("1074", "Budapest", "Dohány utca", "22")),
    ("1075 Budapest, Kovács Béla Kazinczy utca 14", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1075 Budapest, Kazinczy utca 14 (kapukód: 1234)", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("1075 Budapest, Kazinczy utca 14, Hívjon érkezés előtt!", ("1075", "Budapest", "Kazinczy utca", "14")),
    ("KazinczyÃ¼ utca 14 1075 Budapest", ("1075", "Budapest", "Kazinczy utca", "14")),
]

BASE = [
    "1075 Budapest, Kazinczy utca 14",
    "1085 Budapest, Gyulai Pál utca 2",
    "1056 Budapest, Március 15. tér 7",
    "1072 Budapest, Rákóczi út 12-14",
    "1051 Budapest, Széchenyi rakpart 1",
    "1082 Budapest, Futó utca 37",
    "1073 Budapest, Erzsébet körút 12/A",
    "1074 Budapest, Dohány utca 22",
    "1053 Budapest, Kossuth Lajos utca 5",
    "2040 Budaörs, Fő utca 5",
    "2143 Kistarcsa, Fő utca 3",
    "6720 Szeged, Kossuth Lajos sugárút 9",
    "4026 Debrecen, Piac utca 20",
    "1061 Budapest, Andrássy út 28",
    "1065 Budapest, Bajcsy-Zsilinszky út 1",
    "1087 Budapest, Hungária körút 2",
    "1092 Budapest, Ráday utca 31",
    "1146 Budapest, Thököly út 105",
    "2100 Gödöllő, Dózsa György út 10",
    "7621 Pécs, Király utca 8",
]

# Things people put in the field that are not an address. Each is appended or prepended to a clean address.
NOISE_SUFFIX = [
    " szül. 1990.05.12",
    " szül: 1985. 03. 07.",
    " született 1979-11-30",
    " 1990.05.12",
    " 12/05/1990",
    ", tel: +36 20 123 4567",
    ", +36 30 987 6543",
    " 06 20 123 4567",
    ", 20/123-4567",
    ", kapukód: 1234",
    ", csengő: Kovács",
    ", hívjon érkezés előtt",
    ", kovacs.janos@example.com",
    ", https://example.com/track/123",
    ", RR123456789HU",
    ", 1Z999AA10123456784",
    ", portás átveszi",
    ", megjegyzés: este 6 után",
]
NOISE_PREFIX = [
    "Dr. Kiss Péter, ",
    "Özv. Nagy Istvánné, ",
    "1990.05.12 ",
    "szül. 1980. 03. 12. ",
    "+36 20 123 4567 ",
    "06 30 111 2222 ",
]


class GoldenCorpusTest(SimpleTestCase):
    def test_golden(self):
        for raw, (zip_code, city, street, house) in GOLDEN:
            with self.subTest(raw=raw):
                parts = parse_address(raw).parts
                self.assertEqual(
                    (parts["zip"], parts["city"], parts["street"], parts["house"]), (zip_code, city, street, house)
                )

    def test_j_ac6_noise_removed_and_house_number_kept(self):
        """Birth dates, phones, e-mails, notes leave the address, are listed in removed[], and the number survives."""
        cases = 0
        for base in BASE:
            expected = parse_address(base)
            self.assertTrue(expected.parts["street"], base)
            variants = [base + s for s in NOISE_SUFFIX] + [p + base for p in NOISE_PREFIX]
            for raw in variants:
                cases += 1
                with self.subTest(raw=raw):
                    got = parse_address(raw)
                    self.assertEqual(got.parts["house"], expected.parts["house"])
                    self.assertEqual(got.parts["zip"], expected.parts["zip"])
                    self.assertEqual(got.parts["street"], expected.parts["street"])
                    self.assertEqual(got.cleaned, expected.cleaned)
                    self.assertTrue(got.removed, "noise must be listed, never silently lost")
        self.assertGreaterEqual(cases, 200)

    def test_removed_kinds(self):
        r = parse_address("Kazinczy u. 14 1990.05.12 1075 Bp., tel: +36 20 123 4567")
        self.assertTrue({"date", "phone"} <= {x["kind"] for x in r.removed})
        self.assertEqual(r.cleaned, "1075 Budapest, Kazinczy utca 14")

    def test_j_ac7_idempotent(self):
        for raw in [g[0] for g in GOLDEN] + BASE:
            first = parse_address(raw)
            if not first.cleaned:
                continue
            with self.subTest(raw=raw):
                self.assertEqual(parse_address(first.cleaned).cleaned, first.cleaned)

    def test_house_number_after_street_type_is_never_noise(self):
        # 10-digit-looking and date-looking runs right after a street type stay (house numbers / helyrajzi szám)
        r = parse_address("1075 Budapest, Kazinczy utca 2012")
        self.assertEqual(r.parts["house"], "2012")
        self.assertEqual(r.removed, [])

    def test_zip_not_confused_with_house_number(self):
        r = parse_address("Kazinczy utca 1075, 1074 Budapest")
        self.assertEqual((r.parts["zip"], r.parts["house"]), ("1074", "1075"))

    def test_conflict_zip_wins_over_city(self):
        r = parse_address("1075 Szeged, Kazinczy utca 14")
        self.assertEqual(r.parts["city"], "Budapest")
        self.assertTrue(any("zip wins" in s for s in r.steps))

    def test_empty_and_garbage(self):
        for raw in ["", "   ", "???", "1990.05.12", "tel: +36 20 123 4567"]:
            with self.subTest(raw=raw):
                r = parse_address(raw)
                self.assertEqual(r.cleaned, "")
                self.assertFalse(r.ok)

    def test_variants_order_and_street_only_never_auto(self):
        r = parse_address("1072 Budapest, Rákóczi ut 12/A")
        kinds = [v.kind for v in r.variants]
        self.assertEqual(kinds[0], "full")
        self.assertIn("base_number", kinds)
        self.assertEqual(kinds[-1], "street_only")
        self.assertFalse(r.variants[-1].auto_accept)
        self.assertTrue(all(v.auto_accept for v in r.variants[:-1]))
        self.assertEqual(next(v for v in r.variants if v.kind == "base_number").query, "1072 Budapest, Rákóczi út 12")

    def test_unique_clear_margin_only_auto_corrects(self):
        r = parse_address("1075 Budapest, Kazinci utca 14")
        self.assertEqual(r.parts["street"], "Kazinczy utca")
        self.assertTrue(any("street corrected" in s for s in r.steps))
        self.assertIn("as_typed", [v.kind for v in r.variants])

    def test_unknown_street_is_left_alone(self):
        r = parse_address("1075 Budapest, Zzyzx utca 14")
        self.assertEqual(r.parts["street"], "Zzyzx utca")
        self.assertFalse(any("street corrected" in s for s in r.steps))


class UnitTest(SimpleTestCase):
    def test_house_forms(self):
        self.assertEqual(parse_house("12"), ("12", ""))
        self.assertEqual(parse_house("12."), ("12", ""))
        self.assertEqual(parse_house("12/a"), ("12/A", ""))
        self.assertEqual(parse_house("12 A lh. II. em. 5."), ("12", "A lh. II. em. 5"))
        self.assertEqual(parse_house("12-14"), ("12-14", ""))
        self.assertEqual(parse_house("12 2. em. 5. ajtó"), ("12", "2. em. 5. ajtó"))
        self.assertEqual(parse_house(""), ("", ""))

    def test_base_number(self):
        self.assertEqual(base_number("12/A"), "12")
        self.assertEqual(base_number("12-14"), "12")
        self.assertEqual(base_number("hrsz. 12/3"), "hrsz. 12/3")

    def test_distance_and_phonetics(self):
        self.assertEqual(damerau_levenshtein("kazinczi", "kazinczi"), 0)
        self.assertEqual(damerau_levenshtein("kazincz", "kazinzc"), 1)  # transposition
        self.assertEqual(phonetic("Pálya"), phonetic("Pája"))
        self.assertEqual(phonetic("Széll"), phonetic("Szél"))
