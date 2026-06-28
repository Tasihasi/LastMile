"""Generate the UPS courier-route e2e fixture.

This reproduces the *exact signature* of the real, gitignored operational file
`example_files/UPS térkép teszt.xlsx` so CI can test that real-world file shape
without ever committing company data:

  * Sheet name `Munkalap1`
  * Hungarian headers: város, irszám, u, hsz, megj, Cím, kör, <courier names>
  * A per-courier summary count row directly under the header
  * The `Cím` (address) column as an Excel *formula* `=C{r}&" "&D{r}` with no
    cached value — exactly like the source file — so the parser's
    formula-fallback (recompose address from street + house number) is exercised
  * Authentic Budapest District I addresses and the real courier profiles
    (bálint, marci, orsi, laci, simi, ádám, futár7) plus a `fel` (pickup) row

Run from this directory:  python generate_ups_fixture.py
"""

from openpyxl import Workbook

# (város, irszám, u, hsz, megj, kör)
STOPS = [
    ("Budapest", 1011, "Markovits Iván utca", "4", "coyote cafe laverde", "bálint"),
    ("Budapest", 1011, "Pala utca", "6", "", "bálint"),
    ("Budapest", 1011, "Fő utca", "4", "", "bálint"),
    ("Budapest", 1011, "Bem rakpart", "25b", "", "bálint"),
    ("Budapest", 1012, "Pálya utca", "9", "", "marci"),
    ("Budapest", 1012, "Logodi utca", "27b", "vigh gergely gyümidoboz", "marci"),
    ("Budapest", 1012, "Lovas út", "4", "", "marci"),
    ("Budapest", 1013, "Döbrentei utca", "12", "", "orsi"),
    ("Budapest", 1013, "Krisztina körút", "32", "", "orsi"),
    ("Budapest", 1014, "Úri utca", "8", "", "laci"),
    ("Budapest", 1014, "Tárnok utca", "1", "", "laci"),
    ("Budapest", 1015, "Batthyány utca", "3", "", "simi"),
    ("Budapest", 1016, "Gellérthegy utca", "8", "optika", "ádám"),
    ("Budapest", 1117, "Magyar tudósok körútja", "2", "ttk", "fel"),
]

COURIERS = ["bálint", "marci", "orsi", "laci", "simi", "ádám", "futár7"]


def build():
    wb = Workbook()
    ws = wb.active
    ws.title = "Munkalap1"

    # Header row (note the trailing space on "u " matches the source file).
    ws.append(["város", "irszám", "u ", "hsz", "megj", "Cím", "kör", *COURIERS])

    # Summary count row: number of stops assigned to each courier.
    counts = {c: 0 for c in COURIERS}
    for *_, kor in STOPS:
        if kor in counts:
            counts[kor] += 1
    ws.append([None] * 7 + [counts[c] for c in COURIERS])

    # Data rows. Cím is a formula concatenating street (col C) + house no (col D),
    # left uncalculated exactly like the real export.
    for i, (varos, irsz, u, hsz, megj, kor) in enumerate(STOPS):
        excel_row = i + 3  # +1 header, +1 summary, +1 to 1-base
        cim_formula = f'=C{excel_row}&" "&D{excel_row}'
        ws.append([varos, irsz, u, hsz, megj or None, cim_formula, kor])

    wb.save("ups_terkep_teszt.xlsx")
    print(f"Wrote ups_terkep_teszt.xlsx with {len(STOPS)} stops; counts: {counts}")


if __name__ == "__main__":
    build()
