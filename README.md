# LastMile

A delivery route planner for bicycle couriers. Upload a list of delivery addresses, see them on a map, and get an optimized route that follows real roads.

Built as a learning project to explore geospatial APIs, file parsing, and real-time streaming.

![Tech Stack](https://img.shields.io/badge/Django-092E20?style=flat&logo=django&logoColor=white)
![Tech Stack](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black)
![Tech Stack](https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript&logoColor=white)
![Tech Stack](https://img.shields.io/badge/Leaflet-199900?style=flat&logo=leaflet&logoColor=white)

## Documentation

Full user guides and API reference are in the [`docs/`](docs/) folder:

- [Getting Started](docs/getting-started.md) -- login, first route, basic workflow
- [Biker Guide](docs/biker-guide.md) -- delivering, marking stops, map navigation
- [Planner Guide](docs/planner-guide.md) -- dashboard, assigning routes, live tracking
- [File Format Reference](docs/file-formats.md) -- CSV, XLSX, TXT, XML specs and examples
- [API Reference](docs/api-reference.md) -- all REST endpoints

## Features

- **Multi-format file upload** -- CSV, XLSX, TXT (tab-delimited), XML
- **Mixed input** -- rows with coordinates skip geocoding, rows with addresses get geocoded
- **Real-time geocoding** -- pins appear on the map one-by-one as addresses resolve (NDJSON streaming)
- **Route optimization** -- finds the shortest route visiting all stops using the VROOM algorithm
- **Road-following routes** -- route line follows actual roads, not straight lines
- **Interactive map** -- numbered markers, popups, auto-zoom to fit all stops
- **Color-coded markers** -- grey (pending), red (failed), green (geocoded/has coords), blue (optimized)
- **Bulk clustering** -- split large uploads into geographic sub-routes using KMeans (respects ORS 48-stop limit)

## How It Works

```
Upload File  -->  Parse Stops  -->  Geocode Addresses  -->  Optimize Route
  (CSV/XLSX/      (Django)       (Nominatim, streamed     (ORS VROOM +
   TXT/XML)                        via NDJSON)             Directions)
```

1. Upload a file with delivery stop names and addresses (or coordinates)
2. Click **Geocode Addresses** to convert addresses to map coordinates
3. Click **Optimize Route** to calculate the optimal delivery order
4. View the optimized route on the map with numbered stops and a road-following path

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend | Django + Django REST Framework | Robust API framework with ORM |
| Frontend | React + Vite + TypeScript | Fast dev server, type safety |
| Map | Leaflet + React-Leaflet + OpenStreetMap | Free, no API key needed |
| Geocoding | Nominatim | Free, 1 req/sec rate limit |
| Route optimization | OpenRouteService (VROOM) | Free tier, 2000 req/day |
| Route geometry | ORS Directions API | Real road-following paths |
| Clustering | scikit-learn (KMeans) | Geographic splitting of large uploads |
| File parsing | csv, openpyxl, xml.etree | Handles CSV, XLSX, TXT, XML |

**Total cost: $0** -- all APIs are free tier.

## Prerequisites

- Python 3.11+
- Node.js 18+
- An [OpenRouteService](https://openrouteservice.org/) API key (free)

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Tasihasi/delivery-planner.git
cd delivery-planner
```

### 2. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:

```
ORS_API_KEY=your_openrouteservice_api_key_here
```

> Get a free API key at [openrouteservice.org/dev/#/signup](https://openrouteservice.org/dev/#/signup)

Run migrations and start the server:

```bash
python manage.py migrate
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

## File Formats

All formats expect a header row with these columns: `name`, `address`, `lat`, `lng`.

Rows must have a `name` and either an `address` or both `lat`/`lng`. You can mix both in the same file.

### CSV

```csv
name,address,lat,lng
Depot - Keleti Station,,47.5003,19.0841
Pizza King Astoria,Karoly korut 3 Budapest,,
```

### TXT (tab-delimited)

```
name	address	lat	lng
Depot - Keleti Station		47.5003	19.0841
Pizza King Astoria	Karoly korut 3 Budapest		
```

### XLSX

Standard Excel file. First sheet, first row as headers.

### XML

```xml
<deliveries>
  <stop>
    <name>Depot - Keleti Station</name>
    <address></address>
    <lat>47.5003</lat>
    <lng>19.0841</lng>
  </stop>
  <stop>
    <name>Pizza King Astoria</name>
    <address>Karoly korut 3 Budapest</address>
    <lat></lat>
    <lng></lng>
  </stop>
</deliveries>
```

Sample files are included in `backend/planner/sample_data/`.

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload/` | Upload a file, parse stops, create session |
| `GET` | `/api/sessions/{id}/` | Get session with all stops |
| `POST` | `/api/sessions/{id}/geocode/` | Geocode pending stops (streams NDJSON) |
| `GET` | `/api/sessions/{id}/geocode-status/` | Get geocoding progress |
| `POST` | `/api/sessions/{id}/optimize/` | Optimize route, return ordered stops + GeoJSON |
| `POST` | `/api/sessions/{id}/cluster/` | Cluster stops into N geographic sub-routes |
| `POST` | `/api/sessions/{id}/move-stop/` | Move a stop between sibling sub-routes |

### POST /api/upload/

Upload a file as `multipart/form-data` with a `file` field.

**Response** `201`:
```json
{
  "id": "uuid",
  "stops": [
    {
      "id": 1,
      "name": "Depot",
      "raw_address": "",
      "lat": 47.5003,
      "lng": 19.0841,
      "geocode_status": "skipped",
      "geocode_error": "",
      "sequence_order": null
    }
  ],
  "needs_geocoding": true
}
```

### POST /api/sessions/{id}/geocode/

Streams NDJSON (one JSON object per line) as each address is geocoded:

```json
{"stop": {"id": 2, "name": "Pizza King", "lat": 47.4965, "lng": 19.0565, "geocode_status": "success", ...}, "progress": {"current": 1, "total": 9}}
{"stop": {"id": 3, "name": "Spar Blaha", "lat": 47.4963, "lng": 19.0696, "geocode_status": "success", ...}, "progress": {"current": 2, "total": 9}}
```

### POST /api/sessions/{id}/optimize/

**Response** `200`:
```json
{
  "optimized_stops": [
    {"id": 1, "name": "Depot", "sequence_order": 1, ...},
    {"id": 5, "name": "Cafe Szimpla", "sequence_order": 2, ...}
  ],
  "route_geometry": {
    "type": "LineString",
    "coordinates": [[19.0841, 47.5003], [19.0565, 47.4965], ...]
  }
}
```

## Project Structure

```
delivery_planner/
├── backend/
│   ├── config/                # Django project settings
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── planner/               # Django app
│   │   ├── models.py          # DeliverySession + DeliveryStop
│   │   ├── parsers.py         # CSV/XLSX/TXT/XML file parsing
│   │   ├── geocoder.py        # Nominatim geocoding client
│   │   ├── optimizer.py       # ORS route optimization + directions
│   │   ├── clustering.py     # KMeans geographic clustering
│   │   ├── views.py           # API endpoints
│   │   ├── serializers.py     # DRF serializers
│   │   ├── urls.py            # URL routing
│   │   └── sample_data/       # Example upload files
│   ├── .env                   # API keys (gitignored)
│   ├── .env.example           # Template for .env
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/client.ts      # API client (axios + fetch streaming)
│       ├── hooks/
│       │   └── useDeliveryPlanner.ts  # Central state management
│       ├── components/
│       │   ├── FileUpload.tsx     # Drag-and-drop file upload
│       │   ├── DeliveryMap.tsx     # Leaflet map with markers + route
│       │   └── AddressList.tsx     # Sidebar stop list
│       ├── types/index.ts
│       ├── App.tsx
│       └── App.css
├── .gitignore
└── README.md
```

## Technical Notes

- **Coordinate order**: Leaflet uses `[lat, lng]`, ORS APIs use `[lng, lat]`. The conversion happens at the API boundary in `optimizer.py`.
- **Geocoding streaming**: Uses Django's `StreamingHttpResponse` with NDJSON. The frontend reads the stream with the Fetch API's `ReadableStream`, updating the UI as each address resolves.
- **No auth**: This is a demo app. Sessions are UUID-based and ephemeral. No user accounts.
- **SQLite**: Good enough for a demo. Stores sessions and caches geocoding results across page refreshes.
- **Rate limiting**: Nominatim allows 1 request per second. The geocoder enforces this with `time.monotonic()`.

## External APIs

| API | Usage | Rate Limit | Docs |
|-----|-------|-----------|------|
| Nominatim | Address to coordinates | 1 req/sec | [nominatim.org](https://nominatim.org/release-docs/latest/api/Search/) |
| ORS Optimization | Optimal stop order (VROOM) | 2000 req/day | [openrouteservice.org](https://openrouteservice.org/dev/#/api-docs/optimization) |
| ORS Directions | Road-following route geometry | 2000 req/day | [openrouteservice.org](https://openrouteservice.org/dev/#/api-docs/v2/directions) |
| OpenStreetMap Tiles | Map rendering | Fair use | [openstreetmap.org](https://wiki.openstreetmap.org/wiki/Tile_usage_policy) |

## License

This project is for learning and portfolio purposes.
