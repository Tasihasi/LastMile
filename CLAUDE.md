# Delivery Planner -- Claude Context Documentation

> **Self-updating rule**: Any change Claude makes to this project MUST be reflected in this documentation. Update the relevant section(s) of this file whenever you add, modify, or remove features, endpoints, models, components, files, or architectural patterns. This keeps Claude's contextual knowledge accurate across sessions.

## Project Overview

**Delivery Planner** (branded "LastMile") is a full-stack web app for planning and tracking optimized bicycle delivery routes. Users upload delivery stop lists, geocode addresses, optimize route order, and track deliveries in real time. Supports two roles: **bikers** (execute routes) and **planners** (manage all routes, assign to bikers, monitor live).

- **Status**: Learning/portfolio project, actively developed
- **Repo**: GitHub (Tasihasi/delivery-planner)
- **Main branch**: `main`
- **Total cost**: $0 -- all APIs are free tier

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend | Django + Django REST Framework | Django 5.x, DRF 3.15+ |
| Database | SQLite | dev/demo only |
| Frontend | React + Vite + TypeScript | React 19, Vite 8, TS 5.9 |
| Routing | React Router | v7 |
| HTTP Client | Axios (requests) + Fetch API (streaming) | |
| Map | Leaflet + React-Leaflet + OpenStreetMap tiles | Leaflet 1.9, React-Leaflet 5 |
| Geocoding | Nominatim (OpenStreetMap) | 1 req/sec rate limit |
| Route optimization | OpenRouteService (VROOM algorithm) | 2000 req/day free |
| Route geometry | ORS Directions API | same key |
| Clustering | scikit-learn (KMeans) | 1.5+ |
| File parsing | csv, openpyxl, xml.etree | built-in + openpyxl |
| Static files | WhiteNoise | 6.x |
| Linting | Ruff (backend), ESLint (frontend) | |
| CI/CD | GitHub Actions | Python 3.12, Node 20 |
| Hosting | Render (single web service) | Free tier |

---

## Project Structure

```
delivery_planner/
├── backend/
│   ├── config/
│   │   ├── settings.py           # Django config (SQLite, CORS, DRF, TokenAuth)
│   │   ├── urls.py               # Root URL routing -> planner.urls
│   │   ├── asgi.py / wsgi.py
│   ├── planner/                  # Main Django app
│   │   ├── models.py             # DeliverySession, DeliveryStop, UserProfile, SharedRoute
│   │   ├── views.py              # All API endpoints (~580 lines)
│   │   ├── serializers.py        # DRF serializers (~173 lines)
│   │   ├── urls.py               # API route definitions
│   │   ├── geocoder.py           # Nominatim geocoding client
│   │   ├── optimizer.py          # ORS optimization + directions
│   │   ├── clustering.py         # KMeans geographic clustering (scikit-learn)
│   │   ├── parsers.py            # Multi-format file parsing (CSV/XLSX/TXT/XML)
│   │   ├── admin.py / apps.py / tests.py
│   │   ├── migrations/           # 8 migrations (0001-0008)
│   │   ├── management/commands/
│   │   │   └── seed_test_data.py # Generates 3 bikers, 9 routes
│   │   └── sample_data/          # Example CSV/XLSX/XML files + large_delivery_300.csv
│   ├── media/uploads/            # Uploaded files + cached geocodes
│   ├── db.sqlite3
│   ├── requirements.txt          # Django, DRF, CORS, openpyxl, requests, python-dotenv, scikit-learn
│   ├── requirements-dev.txt      # Ruff
│   ├── .env                      # ORS_API_KEY (gitignored)
│   ├── .env.example
│   └── ruff.toml
├── frontend/
│   ├── src/
│   │   ├── main.tsx              # Entry point (AuthContext + React Router)
│   │   ├── App.tsx               # Main app shell, 3 view modes (~480 lines)
│   │   ├── App.css               # All styles (~3300 lines), CSS variables, light/dark
│   │   ├── index.css             # Base styles
│   │   ├── api/
│   │   │   └── client.ts         # Axios + Fetch API client (~261 lines)
│   │   ├── types/
│   │   │   └── index.ts          # TypeScript interfaces (~85 lines)
│   │   ├── hooks/
│   │   │   ├── useAuth.ts        # Auth context provider + hook
│   │   │   ├── useDeliveryPlanner.ts  # Central state (stops, sessions, optimization)
│   │   │   ├── useSettings.ts    # Route settings (start time, dwell, speed, depot)
│   │   │   └── useTheme.ts       # Light/dark theme toggle
│   │   ├── components/
│   │   │   ├── LoginScreen.tsx       # Auth UI (username + role picker)
│   │   │   ├── FileUpload.tsx        # Drag-drop file upload
│   │   │   ├── DeliveryMap.tsx       # Leaflet map (markers, route line, auto-zoom)
│   │   │   ├── AddressList.tsx       # Sidebar stop list (status, actions)
│   │   │   ├── StopDetail.tsx        # Modal popup with stop info
│   │   │   ├── SettingsPanel.tsx     # Route config (depot, time, speed)
│   │   │   ├── SessionList.tsx       # Biker's route history
│   │   │   ├── BikerPicker.tsx       # Dropdown to filter by biker
│   │   │   ├── PlannerDashboard.tsx  # Kanban-style route management
│   │   │   ├── PlannerMapView.tsx    # Aggregate live map (all active routes)
│   │   │   ├── SharedRouteView.tsx   # Public read-only route view
│   │   │   └── FinishedRouteDetail.tsx # Modal with delivery stats
│   │   └── utils/
│   │       └── format.ts         # Duration, distance, time formatting
│   ├── index.html                # HTML entry (Inter font, "LastMile" title)
│   ├── .env.development          # Dev API URL (VITE_API_BASE=http://localhost:8000/api)
│   ├── vite.config.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── eslint.config.js
├── .github/workflows/
│   └── ci.yml                    # Backend lint/test + frontend build
├── build.sh                      # Render build script (frontend + backend)
├── CLAUDE.md                     # This file
├── PLAN.md                       # Tier 1 & 2 implementation roadmap (all completed)
├── README.md                     # Setup docs, API reference
└── .gitignore
```

---

## Data Models

### DeliverySession
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| owner | FK(User) | Nullable -- null = unassigned |
| parent | FK(self) | Nullable -- links sub-routes to parent session (related_name="sub_routes") |
| name | str | Auto-named from filename |
| original_file | FileField | uploads/ |
| created_at | DateTimeField | auto_now_add |
| status | str | `not_started` / `in_progress` / `finished` / `split` |
| started_at | DateTimeField | Nullable, set when biker starts |
| finished_at | DateTimeField | Nullable, set when all stops marked |
| current_stop_index | int | Nullable, tracks next pending stop's sequence_order |
| total_duration | float | Seconds, set after optimization |
| total_distance | float | Meters, set after optimization |
| route_geometry | JSONField | GeoJSON LineString, nullable |
| route_segments | JSONField | Array of `{from_index, to_index, duration, distance}` |

### DeliveryStop
| Field | Type | Notes |
|-------|------|-------|
| id | int | Auto PK |
| session | FK(DeliverySession) | |
| name | str | Required |
| raw_address | str | Address text for geocoding |
| product_code | str | Optional SKU/code |
| recipient_name | str | Optional |
| recipient_phone | str | Optional, clickable tel: link |
| lat / lng | float | Nullable until geocoded |
| geocode_status | str | `pending` / `success` / `failed` / `skipped` |
| geocode_error | str | Error message from Nominatim |
| sequence_order | int | Nullable until optimized (1..N) |
| delivery_status | str | `pending` / `delivered` / `not_received` / `skipped` |

### UserProfile
| Field | Type | Notes |
|-------|------|-------|
| user | OneToOne(User) | |
| role | str | `biker` / `planner` |

### SharedRoute
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key, used in share URL |
| session | FK(DeliverySession) | |
| created_at | DateTimeField | auto_now_add |

### Migrations (8 total)
1. `0001_initial` -- Base Session + Stop
2. `0002_*` -- Recipient fields, product_code
3. `0003_*` -- Auth system (owner, roles, shares)
4. `0004_*` -- Route naming, duration, distance
5. `0005_*` -- Status fields (status, started_at, finished_at, current_stop_index)
6. `0006_*` -- route_geometry (GeoJSON)
7. `0007_*` -- route_segments (timing array)
8. `0008_session_parent_and_split_status` -- parent FK (self-referential) + "split" status choice

---

## API Endpoints

### Authentication
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/login/` | Create user + token (username + role) | None |
| GET | `/api/auth/me/` | Get current user | Token |
| POST | `/api/auth/logout/` | Delete auth token | Token |

### Session Management
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/upload/` | Upload file, create session, parse stops | Token |
| GET | `/api/sessions/` | List sessions (bikers: own, planners: all or ?owner_id=) | Token |
| GET | `/api/sessions/<id>/` | Get session with stops, geometry, segments | Token |
| PATCH | `/api/sessions/<id>/rename/` | Rename route | Planner |
| PATCH | `/api/sessions/<id>/assign/` | Assign to biker | Planner |
| DELETE | `/api/sessions/<id>/delete/` | Delete route | Planner |

### Geocoding & Optimization
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/sessions/<id>/geocode/` | Stream NDJSON, geocode pending stops | Token |
| GET | `/api/sessions/<id>/geocode-status/` | Check progress (pending/success/failed) | Token |
| POST | `/api/sessions/<id>/optimize/` | Optimize route order + geometry + segments | Token |

### Bulk Clustering (Planner)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/sessions/<id>/cluster/` | Cluster stops into N child sessions (KMeans) | Planner |
| POST | `/api/sessions/<id>/move-stop/` | Move a stop between sibling sub-routes | Planner |

**POST cluster/** request: `{"n_routes": 7, "max_stops_per_route": 48}` (both optional, defaults auto-calculated).
Response: `{parent_id, sub_routes[], cluster_summary{total_stops, skipped_stops, n_routes, avg_stops_per_route, min_stops, max_stops}}`.
Parent session status becomes `split`; stops are moved to child sessions.

**POST move-stop/** request: `{"stop_id": 123, "to_session_id": "uuid"}`.
Response: `{stop_id, from_session_id, to_session_id, from_count, to_count}`.
Both sessions must be siblings (same parent).

### Route Lifecycle (Biker)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| PATCH | `/api/sessions/<id>/start/` | Start route (status -> in_progress) | Token |
| PATCH | `/api/sessions/<id>/stops/<stop_id>/status/` | Mark stop (delivered/not_received/skipped) | Token |

Auto-advances `current_stop_index` to next pending stop. Auto-finishes route when all marked.

### Sharing & Planner
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/sessions/<id>/share/` | Create anonymous share link | Token |
| GET | `/api/shared/<share_id>/` | Get shared route | None |
| GET | `/api/users/bikers/` | List all bikers | Planner |
| GET | `/api/sessions/active/` | All in-progress sessions (live map data) | Planner |

---

## Frontend Architecture

### State Management
- **AuthContext** (useAuth.ts) -- Global user + token via Context API, stored in localStorage
- **useDeliveryPlanner** -- Central hook: current session, stops, upload/geocode/optimize state, status tracking
- **useSettings** -- Route parameters persisted to localStorage (start time, dwell, speed, depot)
- **useTheme** -- Light/dark mode toggle (localStorage + OS preference)

### View Modes (App.tsx)
The app has 3 main view modes controlled by state in App.tsx:
1. **Route View** (default for bikers) -- Map + sidebar with stops
2. **Planner Dashboard** -- Kanban columns (unassigned + per-biker)
3. **Live Map** -- Aggregate map of all active routes (planner only)

### Authentication Flow
```
LoginScreen -> POST /api/auth/login/ -> token in localStorage
-> Axios interceptor adds "Authorization: Token <token>" to all requests
-> No passwords, username + role only (demo app)
```

### Key Patterns
- **NDJSON streaming**: Geocoding uses Fetch API ReadableStream, not Axios. UI updates as each address resolves.
- **Coordinate order**: Leaflet = `[lat, lng]`, ORS APIs = `[lng, lat]`. Conversion in `optimizer.py`.
- **Polling**: Live map polls `GET /api/sessions/active/` every 30 seconds (not WebSockets).
- **Stop-based tracking**: Position = next pending stop's sequence_order, not GPS.

---

## External APIs

| API | Purpose | Rate Limit | Config |
|-----|---------|-----------|--------|
| Nominatim | Address -> lat/lng | 1 req/sec (enforced in geocoder.py) | No key |
| OpenRouteService | Route optimization (VROOM) | 2000 req/day | `ORS_API_KEY` in `.env` |
| ORS Directions | Road geometry + segments | Same key | Same key |
| OpenStreetMap Tiles | Map rendering | Fair use | No key |

---

## File Parsing (parsers.py)

Supports CSV, XLSX, TXT (tab-delimited), XML. Each row must have `name` + either `address` OR both `lat`/`lng`. Optional columns: `product_code`, `recipient_name`, `recipient_phone`.

---

## Styling

- **Single CSS file**: `App.css` (~3300 lines) with CSS variables (50+ design tokens)
- **Themes**: Light (default, slate + indigo), Dark (inverted with adjusted map brightness)
- **Responsive**: Mobile-first breakpoints for mobile, tablet, desktop
- **Key class patterns**: `.app`, `.sidebar`, `.map-container`, `.session-card`, `.stop-item`, `.stop-detail-overlay`

---

## Development

### Start Backend
```bash
cd backend
.venv/Scripts/activate  # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver  # http://localhost:8000/api/
```

### Start Frontend
```bash
cd frontend
npm install
npm run dev  # http://localhost:5173
```

### Seed Test Data
```bash
cd backend
python manage.py seed_test_data  # Creates 3 bikers, 9 routes
```

### Environment Variables
- `ORS_API_KEY` in `backend/.env` (get free key at openrouteservice.org)

---

## CI/CD (.github/workflows/ci.yml)

Runs on **all branches** + PRs:
- **Backend**: Python 3.12, `ruff check` + `ruff format --check`, `python manage.py check`, `python manage.py migrate`, `python manage.py test`
- **Frontend**: Node 20, `npx eslint .`, `npx tsc -b`, `npx vite build`

---

## Deployment (Render)

Single web service on Render. Django serves both the API and the built React SPA.

**How it works:**
- `build.sh` (repo root) runs during Render build: installs deps, builds frontend, runs collectstatic + migrate
- **WhiteNoise** middleware serves Vite build output (`frontend/dist/`) at root URLs (e.g. `/assets/xxx.js`, `/favicon.svg`)
- **Catch-all URL pattern** in `config/urls.py` returns `frontend/dist/index.html` for all non-API/admin routes (SPA routing)
- API calls use relative `/api` path in production (no CORS needed, same origin)

**Render settings:**
- Build command: `./build.sh`
- Start command: `cd backend && gunicorn config.wsgi`
- Environment variables: `DEBUG=False`, `SECRET_KEY`, `ORS_API_KEY`, `ALLOWED_HOSTS`
- `RENDER_EXTERNAL_HOSTNAME` is auto-set by Render and added to `ALLOWED_HOSTS`

**Frontend API URL:**
- Production: `/api` (relative, same origin)
- Development: `http://localhost:8000/api` (via `frontend/.env.development`)
- Configurable via `VITE_API_BASE` env var

---

## Conventions & Rules

### Code Style
- **Backend**: Ruff for formatting + linting (see `ruff.toml`)
- **Frontend**: ESLint with React hooks rules, TypeScript strict mode
- **CSS**: All styles in `App.css` using CSS custom properties (no CSS-in-JS, no Tailwind)

### Architecture Patterns
- One Django app (`planner`) for all backend logic
- DRF ViewSets / function-based views in `views.py`
- Custom hooks for all stateful logic (no Redux, no Zustand)
- Leaflet map wrapped in React-Leaflet components
- Token auth (no sessions, no cookies, no passwords)

### Known Limitations
- SQLite only (not production-ready, would need PostgreSQL)
- No password auth (demo uses username-only)
- Polling not WebSockets for live updates
- Stop-based tracking not GPS
- Single vehicle per route (bulk clustering splits into sub-routes, but no true multi-vehicle dispatch)
- CORS whitelist: only localhost:5173
- No file cleanup for uploads

---

## Feature Status

All Tier 1 and Tier 2 features from PLAN.md are **completed**:
- Multi-format upload (CSV, XLSX, TXT, XML)
- Real-time geocoding with NDJSON streaming
- Route optimization (VROOM) with road-following geometry
- Interactive Leaflet map with numbered color-coded markers
- Token-based auth with biker/planner roles
- Route lifecycle (not_started -> in_progress -> finished)
- Stop status tracking (pending -> delivered/not_received/skipped)
- Planner kanban dashboard with drag-drop assignment
- Live aggregate map with 30s polling
- Route sharing via public links
- Dark/light theme
- Responsive layout
- Finished route stats panel

**Bulk Clustering (Phase 1 -- backend only):**
- KMeans geographic clustering of large uploads into sub-routes (scikit-learn)
- Auto-split oversized clusters to respect ORS 48-stop limit
- Parent/child session hierarchy (parent status = "split", children are independent routes)
- Move stops between sibling sub-routes
- 300-address Budapest test CSV for bulk testing

---

## Self-Updating Documentation Rule

**MANDATORY**: When Claude makes ANY change to this project, the relevant section(s) of this CLAUDE.md MUST be updated to reflect the change. This includes but is not limited to:

- Adding/removing/modifying **models or fields** -> update Data Models section
- Adding/removing/modifying **API endpoints** -> update API Endpoints section
- Adding/removing/modifying **components or hooks** -> update Project Structure + Frontend Architecture
- Adding/removing/modifying **files** -> update Project Structure
- Changing **tech stack or dependencies** -> update Tech Stack section
- Adding/removing **features** -> update Feature Status section
- Changing **conventions or patterns** -> update Conventions & Rules section
- Changing **CI/CD pipeline** -> update CI/CD section
- Changing **external API usage** -> update External APIs section
- Changing **styling patterns** -> update Styling section

If a change spans multiple sections, update ALL affected sections. Never leave this documentation stale.

---

## Claude Execution Plans

The `claude_exec_plan/` directory is gitignored and used for storing local-only execution plans. These are detailed, step-by-step implementation plans that Claude creates before executing multi-step work.

**Workflow:**
1. Claude writes a plan file to `claude_exec_plan/` (e.g. `claude_exec_plan/add_tests.md`)
2. Claude executes the plan step by step
3. After completion, the user reviews the work
4. Once the user confirms, the plan file is deleted

**Rules:**
- Plans live in `claude_exec_plan/` and are never committed (gitignored)
- One plan per file, named descriptively (e.g. `fix_auth_bug.md`, `add_websocket_support.md`)
- Delete completed plans after user review
- If a plan is abandoned or superseded, delete it
