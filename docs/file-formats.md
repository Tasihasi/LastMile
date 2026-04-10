# File Format Reference

## Supported File Types

| Extension | Format |
|-----------|--------|
| `.csv` | Comma-separated values |
| `.xlsx` | Excel workbook (first sheet only) |
| `.txt` | Tab-delimited text |
| `.xml` | XML with `<stop>` elements |

## Columns

| Column | Required | Description |
|--------|----------|-------------|
| `name` | Yes | Stop name or identifier |
| `address` | Conditional | Street address (needed if no lat/lng) |
| `lat` | Conditional | Latitude (needed if no address) |
| `lng` | Conditional | Longitude (needed if no address) |
| `product_code` | No | Package or product reference code |
| `recipient_name` | No | Name of the person receiving the delivery |
| `recipient_phone` | No | Phone number (also accepts `phone` as column name) |

**Each row must have** a `name` AND either an `address` OR both `lat`/`lng`. You can mix both in the same file -- rows with coordinates skip geocoding, rows with only an address get geocoded.

Column names are case-insensitive. Spaces are treated as underscores (e.g., "Recipient Name" matches `recipient_name`).

## Examples

### CSV

```csv
name,address,lat,lng,product_code,recipient_name,recipient_phone
Depot - Keleti Station,,47.5003,19.0841,,,
Pizza King,Andrassy ut 12 Budapest,,,PKG-001,John Doe,+36201234567
Sushi Bar,,47.4963,19.0696,PKG-002,Bob Wilson,+36205551234
Coffee House,Vaci utca 10 Budapest,,,PKG-003,Alice Smith,
```

### TXT (tab-delimited)

```
name	address	lat	lng
Depot - Keleti Station		47.5003	19.0841
Pizza King	Andrassy ut 12 Budapest		
Sushi Bar		47.4963	19.0696
```

### XLSX

Standard Excel file. Use the first sheet with column headers in row 1.

### XML

```xml
<deliveries>
  <stop>
    <name>Depot - Keleti Station</name>
    <lat>47.5003</lat>
    <lng>19.0841</lng>
  </stop>
  <stop>
    <name>Pizza King</name>
    <address>Andrassy ut 12 Budapest</address>
    <product_code>PKG-001</product_code>
    <recipient_name>John Doe</recipient_name>
    <recipient_phone>+36201234567</recipient_phone>
  </stop>
</deliveries>
```

## Limits

- **Maximum file size**: 10 MB
- **Supported extensions**: `.csv`, `.xlsx`, `.txt`, `.xml` (auto-detected by extension)
- Rows without a `name` or without both address and coordinates are silently skipped
- There is no hard row limit, but uploads with more than 48 stops will need clustering to optimize (ORS limit)

## Tips

- Empty address fields are fine if coordinates are provided (and vice versa)
- Rows without a `name` or without both address and coordinates are silently skipped
- The file is auto-detected by extension -- make sure your file has the correct one
- Route is automatically named from the filename (e.g., `monday_run.csv` becomes "Monday Run")
- Column names are case-insensitive and spaces are normalized to underscores (e.g., "Recipient Name" matches `recipient_name`)
- You can pre-geocode stops by including `lat`/`lng` columns -- these skip the geocoding step entirely
