# Delivery Planner -- Claude Context Documentation

> **Self-updating rule**: Any change Claude makes to this project MUST be reflected in this documentation. Update the relevant section(s) of this file whenever you add, modify, or remove features, endpoints, models, components, files, or architectural patterns. This keeps Claude's contextual knowledge accurate across sessions.

## Project Overview

**Delivery Planner** (branded "LastMile") is a full-stack web app for planning and tracking optimized bicycle delivery routes. Users upload delivery stop lists, geocode addresses, optimize route order, and track deliveries in real time. Supports two roles: **bikers** (execute routes) and **planners** (manage all routes, assign to bikers, monitor live).

- **Version**: Beta 1.0
- **Status**: Learning/portfolio project, actively developed
- **Repo**: GitHub (Tasihasi/LastMile)
- **Live URL**: https://lastmile-c07a.onrender.com
- **Main branch**: `main` (connected to Render live deployment)
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
| E2E Testing | Playwright | 1.59+ |
| Linting | Ruff (backend), ESLint (frontend) | |
| CI/CD | GitHub Actions | Python 3.12, Node 20 |
| Hosting | Render (single web service) | Free tier |

---

## Project Structure

```
delivery_planner/
├── backend/
│   ├── config/
│   │   ├── settings.py           # Django config (SQLite, CORS, DRF, TokenAuth, HTTPS enforcement, upload limits, logging)
│   │   ├── urls.py               # Root URL routing -> planner.urls
│   │   ├── asgi.py / wsgi.py
│   ├── planner/                  # Main Django app
│   │   ├── models.py             # DeliverySession, DeliveryStop, UserProfile, SharedRoute
│   │   ├── views.py              # All API endpoints (~778 lines)
│   │   ├── serializers.py        # DRF serializers (~205 lines)
│   │   ├── urls.py               # API route definitions
│   │   ├── geocoder.py           # Nominatim geocoding client (with logging + app-identifying User-Agent)
│   │   ├── optimizer.py          # ORS optimization + directions
│   │   ├── clustering.py         # KMeans geographic clustering (scikit-learn)
│   │   ├── parsers.py            # Multi-format file parsing (CSV/XLSX/TXT/XML)
│   │   ├── admin.py / apps.py / tests.py
│   │   ├── migrations/           # 9 migrations (0001-0009)
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
│   │   ├── App.tsx               # Main app shell, 4 view modes (~559 lines)
│   │   ├── App.css               # All styles (~4589 lines), CSS variables, light/dark
│   │   ├── index.css             # Base styles
│   │   ├── api/
│   │   │   └── client.ts         # Axios + Fetch API client (~303 lines)
│   │   ├── types/
│   │   │   └── index.ts          # TypeScript interfaces (~117 lines)
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
│   │   │   ├── PlannerDashboard.tsx  # Kanban-style route management + cluster triggers
│   │   │   ├── ClusterReviewView.tsx # Cluster review: color-coded map, move stops, optimize/assign per route
│   │   │   ├── PlannerMapView.tsx    # Aggregate live map (all active routes)
│   │   │   ├── SharedRouteView.tsx   # Public read-only route view
│   │   │   └── FinishedRouteDetail.tsx # Modal with delivery stats
│   │   └── utils/
│   │       └── format.ts         # Duration, distance, time formatting
│   ├── index.html                # HTML entry (Inter font, "LastMile" title)
│   ├── .env.development          # Dev API URL (VITE_API_BASE=http://localhost:8000/api)
│   ├── e2e/                      # Playwright E2E test suite
│   │   ├── fixtures.ts           # Login helpers, test data paths
│   │   ├── auth.spec.ts          # Auth flow tests (login, logout, role selection)
│   │   ├── biker-journey.spec.ts # Upload, optimize, start, deliver, finish
│   │   ├── planner-journey.spec.ts # Dashboard, assign, rename, delete, live map
│   │   ├── clustering.spec.ts    # Split, cluster review, optimize all, undo
│   │   ├── map-interactions.spec.ts  # Map markers, stop detail, sidebar toggle
│   │   ├── session-list.spec.ts  # Biker session list, empty state, finished section
│   │   ├── settings-theme.spec.ts # Settings panel, theme toggle persistence
│   │   ├── sharing.spec.ts       # Share link, shared route view, invalid link
│   │   └── test-data/            # CSV fixtures for upload tests
│   ├── playwright.config.ts      # Playwright config (webServer: Django + Vite)
│   ├── vite.config.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── eslint.config.js
├── .github/workflows/
│   └── ci.yml                    # Backend lint/test + frontend build + E2E tests
├── build.sh                      # Render build script (frontend + backend)
├── CHANGELOG.md                  # Version history and new features
├── CLAUDE.md                     # This file
├── PLAN.md                       # Tier 1 & 2 implementation roadmap (all completed)
├── README.md                     # Setup docs, features, deployment
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

### Migrations (9 total)
1. `0001_initial` -- Base Session + Stop
2. `0002_*` -- Recipient fields, product_code
3. `0003_*` -- Auth system (owner, roles, shares)
4. `0004_*` -- Route naming, duration, distance
5. `0005_*` -- Status fields (status, started_at, finished_at, current_stop_index)
6. `0006_*` -- route_geometry (GeoJSON)
7. `0007_*` -- route_segments (timing array)
8. `0008_session_parent_and_split_status` -- parent FK (self-referential) + "split" status choice
9. `0009_add_indexes_on_hot_columns` -- db_index on DeliverySession.status, DeliveryStop.delivery_status/geocode_status/sequence_order

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
| DELETE | `/api/sessions/<id>/uncluster/` | Undo split: delete sub-routes, restore stops to parent, reset to not_started. Blocked if any sub-route is in_progress | Planner |

**POST cluster/** request: `{"n_routes": 7, "max_stops_per_route": 48}` (both optional, defaults auto-calculated).
Response: `{parent_id, sub_routes[], cluster_summary{total_stops, skipped_stops, n_routes, avg_stops_per_route, min_stops, max_stops}}`.
Parent session status becomes `split`; stops are moved to child sessions.

**POST move-stop/** request: `{"stop_id": 123, "to_session_id": "uuid"}`.
Response: `{stop_id, from_session_id, to_session_id, from_count, to_count}`.
Both sessions must be siblings (same parent).

**DELETE uncluster/** -- no request body.
Response: `{message, session_id, stops_restored, sub_routes_deleted}`.
Fails with 409 if any sub-route has status `in_progress`. Parent status resets to `not_started`; all child sessions and their stops are deleted; original stops are restored to parent.

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
The app has 4 main view modes controlled by state in App.tsx:
1. **Route View** (default for bikers) -- Map + sidebar with stops
2. **Planner Dashboard** -- Kanban columns (unassigned + per-biker)
3. **Live Map** -- Aggregate map of all active routes (planner only)
4. **Cluster Review** -- Color-coded map + sidebar for reviewing/editing clustered sub-routes (planner only, accessed from "split" sessions in dashboard)

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
- **Cluster colors**: 10 distinct colors for cluster markers (red, blue, green, purple, orange, teal, pink, brown, indigo, cyan), cycled by cluster index.
- **ClusterBanner**: Extracted component in PlannerDashboard -- renders above SessionCard in a `.session-card-wrapper`, uses connected border-radius pattern (banner rounded top, card rounded bottom).
- **Re-optimize confirmation**: In-progress routes show a ghost "Re-optimize Route" button with inline confirm/cancel bar before executing.
- **Mobile back button**: Bikers get a back button in mobile upload view to return to map/session view.

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

- **Single CSS file**: `App.css` (~4589 lines) with CSS variables (50+ design tokens)
- **Themes**: Light (default, slate + indigo), Dark (inverted with adjusted map brightness)
- **Responsive**: Mobile-first breakpoints for mobile, tablet, desktop. Dashboard fully optimized for mobile (centered columns, touch targets, hidden drag handles)
- **Key class patterns**: `.app`, `.sidebar`, `.map-container`, `.session-card`, `.stop-item`, `.stop-detail-overlay`, `.session-card-wrapper`, `.cluster-banner`, `.reoptimize-confirm`

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

### Run E2E Tests
```bash
cd frontend
npx playwright install chromium    # First time only
npm run test:e2e                   # Runs Playwright (auto-starts Django + Vite)
npm run test:e2e:ui                # Interactive Playwright UI mode
```
E2E tests require `E2E_MOCK=true` env var on the backend (set automatically by playwright.config.ts webServer).

---

## CI/CD (.github/workflows/ci.yml)

Runs on **all branches** + PRs:
- **Backend**: Python 3.12, `ruff check` + `ruff format --check`, `python manage.py check`, `python manage.py migrate`, `python manage.py test`
- **Frontend**: Node 20, `npx eslint .`, `npx tsc -b`, `npx vite build`
- **E2E Tests** (PRs to main/production only): Depends on Backend + Frontend jobs passing first. Playwright Chromium tests against real Django backend (with mocked external APIs via `E2E_MOCK=true`) + Vite dev server. Uploads Playwright report as artifact on failure.

---

## Deployment (Render)

Single web service on Render. Django serves both the API and the built React SPA.

**How it works:**
- `build.sh` (repo root) runs during Render build: installs deps, builds frontend, runs collectstatic + migrate
- **WhiteNoise** middleware serves Vite build output (`frontend/dist/`) at root URLs (e.g. `/assets/xxx.js`, `/favicon.svg`)
- **Catch-all URL pattern** in `config/urls.py` returns `frontend/dist/index.html` for all non-API/admin routes (SPA routing)
- API calls use relative `/api` path in production (no CORS needed, same origin)

**Render settings:**
- Deploys from `main` branch (auto-deploy on push)
- Build command: `./build.sh`
- Start command: `cd backend && gunicorn config.wsgi`
- Root directory: empty (repo root)
- Environment variables: `DEBUG=False`, `SECRET_KEY`, `ORS_API_KEY`, `NODE_VERSION=20`
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
- **Query optimization**: List views use `_annotate_session_list()` with `Count`/`Subquery` annotations + `select_related("owner")` to avoid N+1; serializers check for `_annotated` attributes with `hasattr()` fallback for single-object usage
- **Production security**: HTTPS enforcement (HSTS, SSL redirect, secure cookies) auto-enabled when `DEBUG=False`
- **Production logging**: `planner.*` loggers at WARNING level to console; geocoder logs Nominatim request failures and empty results

### Known Limitations
- SQLite only (not production-ready, would need PostgreSQL)
- No password auth (demo uses username-only)
- Polling not WebSockets for live updates
- Stop-based tracking not GPS
- Single vehicle per route (bulk clustering splits large uploads into sub-routes of max 48 stops each, but no true multi-vehicle dispatch)
- CORS whitelist: only localhost:5173 (configurable via env)
- No file cleanup for uploads
- File upload limit: 10 MB

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

**Bulk Clustering (fully completed -- all 3 phases):**
- KMeans geographic clustering of large uploads into sub-routes (scikit-learn)
- Auto-split oversized clusters to respect ORS 48-stop limit
- Parent/child session hierarchy (parent status = "split", children are independent routes)
- Move stops between sibling sub-routes
- 300-address Budapest test CSV for bulk testing
- ClusterReviewView with color-coded cluster map, collapsible cluster cards, per-route optimize/assign actions, move-stop controls
- PlannerDashboard "Split into Routes" button on sessions with >48 stops, "Split Routes" section for reviewing parent sessions
- Child sessions filtered out of normal kanban view (parent_id != null hidden)
- Undo split (DELETE uncluster/) -- reverts clustering, restores stops to parent, blocked if any sub-route is in progress
- Bikers no longer see split parent sessions in session list
- start_route rejects split sessions with clear error message
- "Undo Split" button in ClusterReviewView header
- Empty route warning in sub-route cards (when all stops moved out)
- Delete button for empty sub-routes
- Skipped stops count indicator (non-geocoded stops from parent)
- New TypeScript types: ClusterResponse, ClusterSubRoute, ClusterSummary, MoveStopResponse
- New API client functions: clusterSession(), moveStop(), unclusterSession()

**Backend Hardening (completed):**
- Production HTTPS enforcement: SECURE_SSL_REDIRECT, HSTS, secure cookies (gated by DEBUG=False)
- File upload size limits: 10 MB (DATA_UPLOAD_MAX_MEMORY_SIZE + FILE_UPLOAD_MAX_MEMORY_SIZE)
- Database indexes on hot columns: DeliverySession.status, DeliveryStop.delivery_status/geocode_status/sequence_order
- N+1 query elimination: `list_sessions` uses annotated queryset (Count + Subquery + select_related); `active_sessions` computes counts from prefetched stops in Python
- Annotation-aware serializers: SessionListSerializer and ActiveSessionSerializer use pre-computed annotations when available, with fallback queries for single-object usage

**E2E Testing (completed):**
- Playwright E2E test suite covering full user journeys: auth, upload, geocoding, optimization, route lifecycle, planner dashboard, clustering, sharing, settings, theme, map interactions, session list
- E2E mock mode (`E2E_MOCK=true` env var): geocoder.py returns deterministic fake Budapest-area coordinates; optimizer.py returns angle-sorted order with straight-line geometry -- no external API calls in CI
- CI job runs E2E tests only on PRs to main/production, after backend+frontend jobs pass
- Test data: CSV fixtures with pre-geocoded stops (`e2e/test-data/`) + seeded data from `seed_test_data` command
- Playwright config auto-starts Django backend (with mock + seed) and Vite dev server
- ESLint excludes `e2e/` and `playwright.config.ts` (Playwright uses Node-style imports)
- Playwright report uploaded as CI artifact on failure

**Mobile & UX Polish (completed):**
- Mobile back button for bikers to exit upload/map view
- Planner dashboard fully optimized for mobile (centered columns, 480px max-width, touch-friendly 32px buttons, hidden drag handles)
- ClusterBanner extracted from SessionCard (connected banner-above-card pattern)
- Geocode/optimize buttons hidden for in-progress and finished routes
- Re-optimize ghost button for in-progress routes with inline confirmation prompt
- Split Routes column icon sized correctly via dashboard-column-biker wrapper

**Production Observability (completed):**
- Django LOGGING config surfaces `planner.*` warnings/errors to gunicorn console output
- Geocoder logs actual Nominatim errors (HTTP failures, empty results, parse errors) instead of silently returning None
- Nominatim User-Agent includes app URL per usage policy (`DeliveryPlannerDemo/1.0 (lastmile-c07a.onrender.com)`)

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

## User & GitHub Documentation Rule

**MANDATORY**: Before creating any PR, Claude MUST ensure that user-facing documentation is up to date:

1. **CHANGELOG.md** -- Add new features/fixes under the current version section. If the change warrants a new version, create a new version section.
2. **README.md** -- Update the "What's New" section if the feature is user-visible. Update the Features list, API table, or Project Structure if affected.
3. **docs/** files -- Update the relevant guide(s):
   - New/changed **biker features** -> update `docs/biker-guide.md`
   - New/changed **planner features** -> update `docs/planner-guide.md`
   - New/changed **API endpoints** -> update `docs/api-reference.md`
   - New/changed **file parsing** -> update `docs/file-formats.md`
   - New/changed **onboarding flow** -> update `docs/getting-started.md`
4. **Version bumps** -- When a significant milestone is reached, bump the version in CHANGELOG.md, README.md, docs/README.md, and docs/api-reference.md.

This rule applies to ALL PRs, not just feature PRs. Bug fixes that change user-visible behavior must also update docs.

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
