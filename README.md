# LastMile

> **Beta 1.0.1** -- [Changelog](CHANGELOG.md) | [Live Demo](https://lastmile-c07a.onrender.com)

A full-stack delivery route planner for bicycle couriers. Upload delivery addresses, geocode them on a map, optimize route order, split large uploads into sub-routes, and track deliveries in real time. Supports two roles: **bikers** (execute routes) and **planners** (manage, assign, and monitor).

Built as a learning project to explore geospatial APIs, file parsing, real-time streaming, and role-based multi-user workflows.

![Tech Stack](https://img.shields.io/badge/Django-092E20?style=flat&logo=django&logoColor=white)
![Tech Stack](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=white)
![Tech Stack](https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript&logoColor=white)
![Tech Stack](https://img.shields.io/badge/Leaflet-199900?style=flat&logo=leaflet&logoColor=white)
![Tech Stack](https://img.shields.io/badge/Playwright-2EAD33?style=flat&logo=playwright&logoColor=white)

## Documentation

Full user guides and API reference are in the [`docs/`](docs/) folder:

- [Getting Started](docs/getting-started.md) -- login, first route, basic workflow
- [Biker Guide](docs/biker-guide.md) -- delivering, marking stops, map navigation
- [Planner Guide](docs/planner-guide.md) -- dashboard, assigning routes, clustering, live tracking
- [File Format Reference](docs/file-formats.md) -- CSV, XLSX, TXT, XML specs and examples
- [API Reference](docs/api-reference.md) -- all REST endpoints with request/response examples
- [Changelog](CHANGELOG.md) -- version history and new features

## What's New in Beta 1.0.1

- **Toast notifications** for share, rename, delete, assign, and undo-split actions
- **Header user menu** -- kebab dropdown consolidates Help, Theme, and Sign Out; the username is no longer an instant-logout button
- **Undo Split confirmation** prevents accidental destructive cascades
- **Auto-select in-progress route** drops bikers straight into their active delivery on login
- **Sorted stop list** in the biker sidebar matches the numbered map markers after optimization
- **Esc key** closes stop-detail and finished-route modals
- **Tablet kanban** -- the planner dashboard stays 2-column on iPad-portrait viewports (640-768px)
- **Mobile header kebab** below 380px keeps Sign Out reachable on ultra-narrow screens

### Beta 1.0 Highlights

- Bulk clustering: split large uploads (50+ stops) into geographic sub-routes with KMeans
- Cluster review view: color-coded map, move stops between routes, optimize/assign per sub-route
- Mobile-optimized planner dashboard with centered columns and touch-friendly buttons
- Re-optimize in-progress routes with confirmation prompt
- E2E test suite (Playwright) covering all major user journeys
- Production deployment on Render with logging and Nominatim diagnostics
- Dark/light theme with OS preference detection

See [CHANGELOG.md](CHANGELOG.md) for the complete feature list.

## Features

### Core
- **Multi-format file upload** -- CSV, XLSX, TXT (tab-delimited), XML
- **Mixed input** -- rows with coordinates skip geocoding, rows with addresses get geocoded
- **Real-time geocoding** -- pins appear on the map one-by-one as addresses resolve (NDJSON streaming)
- **Route optimization** -- finds the shortest route visiting all stops using the VROOM algorithm
- **Road-following routes** -- route line follows actual roads, not straight lines
- **Interactive map** -- numbered markers, popups, auto-zoom to fit all stops
- **Color-coded markers** -- grey (pending), red (failed), green (geocoded), blue (optimized)

### Authentication & Roles
- **Token-based auth** -- username + role login (no passwords, demo app)
- **Biker role** -- sees own routes, delivers stops, tracks progress
- **Planner role** -- manages all routes, assigns to bikers, monitors live

### Planner Features
- **Kanban dashboard** -- drag-and-drop route assignment across biker columns
- **Bulk clustering** -- split large uploads into geographic sub-routes using KMeans (respects ORS 48-stop limit)
- **Cluster review** -- color-coded map, move stops between sub-routes, optimize/assign individually
- **Live map** -- aggregate view of all active routes with 30-second auto-refresh
- **Route lifecycle management** -- rename, delete, assign, share routes

### Biker Features
- **Route execution** -- start route, mark stops (delivered / not received / skipped)
- **Auto-advance** -- current stop updates automatically after marking
- **Re-optimize** -- re-optimize in-progress routes with confirmation prompt
- **Stop details** -- arrival times, recipient info, tappable phone numbers

### Mobile & UX
- **Responsive design** -- mobile-optimized dashboard, sidebar toggle, touch targets
- **Dark/light theme** -- toggle with OS preference detection, persisted in browser
- **Route sharing** -- public read-only links (no login required)
- **Finished route stats** -- success rate, timeline, stop-by-stop breakdown

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

## Bulk Delivery Planning

For large uploads (50+ stops), LastMile splits deliveries into manageable routes using geographic clustering:

```
Upload 300 stops  -->  Geocode all  -->  Split into Routes  -->  Review clusters
                                          (KMeans, max 48       (color-coded map,
                                           stops each)           move stops between)

  -->  Optimize each route  -->  Assign to bikers  -->  Bikers deliver normally
        (ORS VROOM +              (planner picks         (each biker sees their
         Directions x N)           from biker list)       route as usual)
```

- Clustering uses KMeans on geographic coordinates, auto-splitting any cluster that exceeds the ORS 48-stop limit
- Planners review clusters on a color-coded map and can move stops between sub-routes before optimizing
- Each sub-route is optimized independently (2 ORS API calls each: VROOM + Directions)
- Undo split is available as long as no sub-route has been started by a biker
- Non-geocoded stops are skipped during clustering and reported in the UI

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
| Auth | DRF TokenAuthentication | Simple token-based auth with roles |
| Static files | WhiteNoise | Serves frontend build in production |
| E2E Testing | Playwright | Full user journey tests |
| Hosting | Render | Free tier, auto-deploy from main |

**Total cost: $0** -- all APIs are free tier.

## Live Demo

The app is deployed at **[lastmile-c07a.onrender.com](https://lastmile-c07a.onrender.com)**.

> Note: Render free tier may take 30-60 seconds to wake up on first visit.

## Prerequisites

- Python 3.11+
- Node.js 18+
- An [OpenRouteService](https://openrouteservice.org/) API key (free)

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Tasihasi/LastMile.git
cd LastMile
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

### 4. Seed test data (optional)

```bash
cd backend
python manage.py seed_test_data  # Creates 3 bikers, 9 routes
```

## File Formats

All formats expect a header row with these columns: `name`, `address`, `lat`, `lng`.

Rows must have a `name` and either an `address` or both `lat`/`lng`. You can mix both in the same file. Optional columns: `product_code`, `recipient_name`, `recipient_phone`.

See [File Format Reference](docs/file-formats.md) for full details and examples.

## API Reference

See [docs/api-reference.md](docs/api-reference.md) for full endpoint documentation.

### Quick Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login/` | Login (username + role) |
| `GET` | `/api/auth/me/` | Current user |
| `POST` | `/api/auth/logout/` | Logout |
| `POST` | `/api/upload/` | Upload file, create session |
| `GET` | `/api/sessions/` | List sessions |
| `GET` | `/api/sessions/{id}/` | Get session details |
| `POST` | `/api/sessions/{id}/geocode/` | Geocode stops (NDJSON stream) |
| `POST` | `/api/sessions/{id}/optimize/` | Optimize route order |
| `POST` | `/api/sessions/{id}/cluster/` | Split into sub-routes (KMeans) |
| `POST` | `/api/sessions/{id}/move-stop/` | Move stop between sub-routes |
| `DELETE` | `/api/sessions/{id}/uncluster/` | Undo split |
| `PATCH` | `/api/sessions/{id}/start/` | Start route |
| `PATCH` | `/api/sessions/{id}/stops/{stop_id}/status/` | Mark stop status |
| `PATCH` | `/api/sessions/{id}/assign/` | Assign to biker |
| `PATCH` | `/api/sessions/{id}/rename/` | Rename route |
| `DELETE` | `/api/sessions/{id}/delete/` | Delete route |
| `POST` | `/api/sessions/{id}/share/` | Create share link |
| `GET` | `/api/shared/{share_id}/` | View shared route (no auth) |
| `GET` | `/api/sessions/active/` | Active sessions (live map) |
| `GET` | `/api/users/bikers/` | List bikers |

## Project Structure

```
LastMile/
├── backend/
│   ├── config/
│   │   ├── settings.py           # Django config (auth, CORS, HTTPS, logging, upload limits)
│   │   ├── urls.py               # Root URL routing + SPA catch-all
│   │   └── wsgi.py
│   ├── planner/
│   │   ├── models.py             # DeliverySession, DeliveryStop, UserProfile, SharedRoute
│   │   ├── views.py              # All API endpoints
│   │   ├── serializers.py        # DRF serializers
│   │   ├── urls.py               # API route definitions
│   │   ├── geocoder.py           # Nominatim geocoding (with logging)
│   │   ├── optimizer.py          # ORS optimization + directions
│   │   ├── clustering.py         # KMeans geographic clustering
│   │   ├── parsers.py            # Multi-format file parsing
│   │   ├── management/commands/
│   │   │   └── seed_test_data.py # Generates test data
│   │   └── sample_data/          # Example files
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.tsx              # Entry point (AuthContext + Router)
│   │   ├── App.tsx               # Main app shell, view mode switching
│   │   ├── App.css               # All styles (CSS variables, light/dark theme)
│   │   ├── api/
│   │   │   └── client.ts         # Axios + Fetch API client
│   │   ├── types/
│   │   │   └── index.ts          # TypeScript interfaces
│   │   ├── hooks/
│   │   │   ├── useAuth.ts        # Auth context + token management
│   │   │   ├── useDeliveryPlanner.ts  # Central state management
│   │   │   ├── useSettings.ts    # Route settings (depot, time, speed)
│   │   │   ├── useTheme.ts       # Light/dark theme toggle
│   │   │   └── useToast.ts       # Toast notification context + hook
│   │   ├── components/
│   │   │   ├── LoginScreen.tsx       # Auth UI (username + role picker)
│   │   │   ├── FileUpload.tsx        # Drag-drop file upload
│   │   │   ├── DeliveryMap.tsx       # Leaflet map (markers, route line)
│   │   │   ├── AddressList.tsx       # Sidebar stop list (sorted by sequence_order)
│   │   │   ├── StopDetail.tsx        # Stop info popup (Esc to close)
│   │   │   ├── SettingsPanel.tsx     # Route config (depot, time, speed)
│   │   │   ├── SessionList.tsx       # Biker's route history (auto-selects in-progress route)
│   │   │   ├── BikerPicker.tsx       # Biker filter dropdown
│   │   │   ├── PlannerDashboard.tsx  # Kanban dashboard + cluster triggers
│   │   │   ├── ClusterReviewView.tsx # Cluster review (color-coded map)
│   │   │   ├── PlannerMapView.tsx    # Live aggregate map
│   │   │   ├── SharedRouteView.tsx   # Public read-only route view
│   │   │   ├── FinishedRouteDetail.tsx # Delivery stats modal (Esc to close)
│   │   │   └── ToastContainer.tsx    # Renders queued toast notifications
│   │   └── utils/
│   │       └── format.ts         # Duration, distance, time formatting
│   ├── e2e/                      # Playwright E2E tests
│   │   ├── fixtures.ts
│   │   ├── auth.spec.ts
│   │   ├── biker-journey.spec.ts
│   │   ├── planner-journey.spec.ts
│   │   ├── clustering.spec.ts
│   │   ├── map-interactions.spec.ts
│   │   ├── session-list.spec.ts
│   │   ├── settings-theme.spec.ts
│   │   ├── sharing.spec.ts
│   │   └── test-data/
│   └── playwright.config.ts
├── docs/                         # User & developer documentation
├── .github/workflows/ci.yml     # CI: lint, build, E2E tests
├── build.sh                      # Render build script
├── CHANGELOG.md                  # Version history
└── CLAUDE.md                     # Claude context documentation
```

## Deployment

Deployed on [Render](https://render.com) (free tier). Django serves both the API and the built React SPA via WhiteNoise.

- **Build command**: `./build.sh`
- **Start command**: `cd backend && gunicorn config.wsgi`
- **Environment variables**: `DEBUG=False`, `SECRET_KEY`, `ORS_API_KEY`, `NODE_VERSION=20`
- Auto-deploys from `main` branch

## Technical Notes

- **Authentication**: Token-based auth via DRF TokenAuthentication. Login creates a user with a role (biker/planner). Token stored in localStorage, sent via `Authorization: Token <token>` header.
- **Coordinate order**: Leaflet uses `[lat, lng]`, ORS APIs use `[lng, lat]`. Conversion happens in `optimizer.py`.
- **Geocoding streaming**: Uses Django's `StreamingHttpResponse` with NDJSON. The frontend reads with Fetch API `ReadableStream`, updating the UI as each address resolves.
- **SQLite**: Development and demo database. Would need PostgreSQL for production scale.
- **Rate limiting**: Nominatim allows 1 request per second, enforced in `geocoder.py`.
- **Clustering**: KMeans on geographic coordinates. Auto-splits clusters exceeding 48 stops (ORS VROOM limit). Parent session status becomes "split"; child sessions are independent routes.

## External APIs

| API | Usage | Rate Limit | Docs |
|-----|-------|-----------|------|
| Nominatim | Address to coordinates | 1 req/sec | [nominatim.org](https://nominatim.org/release-docs/latest/api/Search/) |
| ORS Optimization | Optimal stop order (VROOM) | 2000 req/day | [openrouteservice.org](https://openrouteservice.org/dev/#/api-docs/optimization) |
| ORS Directions | Road-following route geometry | 2000 req/day | [openrouteservice.org](https://openrouteservice.org/dev/#/api-docs/v2/directions) |
| OpenStreetMap Tiles | Map rendering | Fair use | [openstreetmap.org](https://wiki.openstreetmap.org/wiki/Tile_usage_policy) |

## License

This project is for learning and portfolio purposes.
