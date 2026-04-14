import csv
import io

from defusedxml import ElementTree as ET
from openpyxl import load_workbook


def _normalize_row(row: dict) -> dict:
    """Normalize a parsed row into {name, address, lat, lng, product_code, recipient_name, recipient_phone}."""
    name = (row.get("name") or "").strip()
    address = (row.get("address") or "").strip()
    product_code = (row.get("product_code") or "").strip()
    recipient_name = (row.get("recipient_name") or "").strip()
    recipient_phone = (row.get("recipient_phone") or row.get("phone") or "").strip()
    lat = row.get("lat")
    lng = row.get("lng")

    if lat is not None and lat != "":
        try:
            lat = float(lat)
        except (ValueError, TypeError):
            lat = None
    else:
        lat = None

    if lng is not None and lng != "":
        try:
            lng = float(lng)
        except (ValueError, TypeError):
            lng = None
    else:
        lng = None

    return {
        "name": name,
        "address": address,
        "product_code": product_code,
        "recipient_name": recipient_name,
        "recipient_phone": recipient_phone,
        "lat": lat,
        "lng": lng,
    }


def _validate_rows(rows: list[dict]) -> list[dict]:
    """Validate and filter parsed rows. Each row must have a name and either address or coordinates."""
    valid = []
    for row in rows:
        if not row["name"]:
            continue
        has_coords = row["lat"] is not None and row["lng"] is not None
        has_address = bool(row["address"])
        if has_coords or has_address:
            valid.append(row)
    return valid


def _normalize_header(header: str) -> str:
    """Normalize a header name to lowercase, stripped."""
    return header.strip().lower().replace(" ", "_")


def parse_csv(file) -> list[dict]:
    """Parse a comma-separated upload into normalized stop dicts.

    Strips a UTF-8 BOM if present so spreadsheets exported by Excel parse
    cleanly. Headers are case- and whitespace-insensitive.
    """
    content = file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    reader.fieldnames = [_normalize_header(f) for f in reader.fieldnames]
    rows = [_normalize_row(row) for row in reader]
    return _validate_rows(rows)


def parse_txt(file) -> list[dict]:
    """Parse a tab-delimited upload into normalized stop dicts.

    Same header handling as `parse_csv` but uses tab as the delimiter.
    """
    content = file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content), delimiter="\t")
    reader.fieldnames = [_normalize_header(f) for f in reader.fieldnames]
    rows = [_normalize_row(row) for row in reader]
    return _validate_rows(rows)


def parse_xlsx(file) -> list[dict]:
    """Parse the active sheet of an XLSX upload into normalized stop dicts.

    Reads the workbook in read-only mode for memory efficiency on large files.
    Only the *first* (active) sheet is parsed; additional sheets are ignored.
    """
    wb = load_workbook(file, read_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)

    headers = [_normalize_header(str(h or "")) for h in next(rows_iter)]
    rows = []
    for row_values in rows_iter:
        row_dict = dict(zip(headers, row_values, strict=False))
        rows.append(_normalize_row(row_dict))

    wb.close()
    return _validate_rows(rows)


def parse_xml(file) -> list[dict]:
    """Parse an XML upload (root with `<stop>` children) into normalized stop dicts.

    Uses defusedxml to defend against XXE / billion-laughs payloads from
    user-supplied files.
    """
    content = file.read()
    root = ET.fromstring(content)

    rows = []
    for stop in root.findall("stop"):
        row = {
            "name": (stop.findtext("name") or "").strip(),
            "address": (stop.findtext("address") or "").strip(),
            "product_code": (stop.findtext("product_code") or "").strip(),
            "recipient_name": (stop.findtext("recipient_name") or "").strip(),
            "recipient_phone": (stop.findtext("recipient_phone") or stop.findtext("phone") or "").strip(),
            "lat": (stop.findtext("lat") or "").strip(),
            "lng": (stop.findtext("lng") or "").strip(),
        }
        rows.append(_normalize_row(row))

    return _validate_rows(rows)


PARSERS = {
    "text/csv": parse_csv,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": parse_xlsx,
    "text/plain": parse_txt,
    "text/xml": parse_xml,
    "application/xml": parse_xml,
}

EXTENSION_MAP = {
    ".csv": parse_csv,
    ".xlsx": parse_xlsx,
    ".txt": parse_txt,
    ".xml": parse_xml,
}


def parse_file(file, filename: str) -> list[dict]:
    """Parse an uploaded file based on its extension. Returns list of normalized stop dicts."""
    import os

    ext = os.path.splitext(filename)[1].lower()
    parser = EXTENSION_MAP.get(ext)
    if parser is None:
        raise ValueError(f"Unsupported file format: {ext}. Supported: .csv, .xlsx, .txt, .xml")
    return parser(file)
