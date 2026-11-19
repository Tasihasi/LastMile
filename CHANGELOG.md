# Changelog

All notable changes to LastMile are documented here.

Format: features are grouped by category. Each version includes a release date and summary.

---

## Unreleased

### Must conditions (geocoding and optimization)
- **Addresses land where they really are.** Nominatim is restricted to Hungary / Budapest and a hit outside Budapest counts as "not found". The offline mock places an address inside its postal code's area instead of at a random point.
- **Routes are truly optimized.** The offline optimizer is nearest neighbour + 2-opt (was an angle sort), the split time estimate uses the same optimized tour, and optimize fails with an error when road geometry cannot be fetched (was: silent straight lines).
- **Real Services Smoke (CI).** `manage.py smoke_real_services` checks real Nominatim geocoding and real ORS road routing; the E2E job now waits for it and for the Production Smoke job. Geocoder picks among several Nominatim candidates (postcode, else nearest the zip centroid/depot) instead of trusting the first hit.
- The two rulings are written down next to the 15-minute ruling in `CLAUDE.md`.

### Route splitting
- **Zones are edited by planners.** New "Zones" button in the main menu: add, edit and delete zones (groups of postal codes). Zones are stored in the database (seeded with the 16 from the daily sheet) and drive the zone-first split and the split labels; a postal code can belong to one zone only. API: `POST /api/zones/`, `PUT`/`DELETE /api/zones/<id>/` (planner only).
- **Removed the "Single zip/district" lock** from the split dialog; zones replace it.
- **Postal codes are never split across routes.** Splitting a route (automatic or with biker assignments) now keeps every stop of one irányítószám on a single route, replacing the stop-level KMeans split. Zips are placed whole, largest first, onto the nearest route with room. A zip bigger than the route size stays whole and is reported in `oversized_zips`; stops without a postal code go together onto the smallest route and are listed in `unzipped_stop_ids` (both new fields on the `POST /api/sessions/<id>/cluster/` response). If no stop has a postal code at all, the old geographic split is used. Sub-routes now keep the stops' `postal_code`.
- **Split warning.** The split review shows a banner "N irányítószám több körben szerepel: 1082 (Route_1: 4, Route_2: 2)" whenever a postal code is on more than one route (e.g. after moving a stop), with a chip on each affected route; clicking a zip highlights its stops. It is informational and never blocks optimizing. API: `zip_conflicts` on the cluster and move-stop responses and on `GET /api/sessions/<id>/` of a split route.
- **Move a whole postal code to another biker.** "Move zip…" in the split review (next to each warned zip in the banner, and per zip in an expanded route) opens a window showing each route's stop count before and after; confirming moves every stop of that zip. API: `POST /api/sessions/<id>/move-zip/` with `zip` or `zone_id`; atomic, and touched routes need re-optimizing.
- **Zone-first allocation (backend).** When split assignments carry `window_minutes` (and optionally `multiplier`), whole zones are given to bikers so each fills its time window (the 7.5 % overrun is only used as overflow and flagged with `uses_overrun`; bikers the windows do not need get no empty route and are listed in `unused_bikers`; mixed window/lock payloads are rejected); `planner/timing.py` holds the time constants, `planner/zone_allocation.py` the algorithm. The cluster response adds `unassigned_zones` and per-route `load_minutes` / `capacity_minutes` / `zones`. The wizard does not send windows yet (backlog B1).
- **Minimal zone splitting (backend + review label).** When whole zones don't fit the bikers' windows, the fewest possible zones are broken up, always along whole postal codes (`planner/zone_splitting.py`). The split review shows e.g. "Zóna Z12 szétbontva: 1082→Route_1, 1083→Route_2". A zip too big for any window stays whole and the route is flagged `over_capacity`.

### Zones
- Zone config (`backend/planner/zones.json`, `planner/zones.py`): the 34 postal codes of districts V-IX grouped into 16 sorting zones, from the customer's sheet. New planner-only `GET /api/zones/`. Zips outside the config have no zone.

### Developer tooling
- Backlog A0: deterministic Budapest zip fixtures (`planner/testing/zip_fixtures.py`: `make_stops`, `make_session`, `REALISTIC_DAY`) and a zone-first feasibility spike report (`docs/backlog/A0-spike-report.md`). Test-only; no production behaviour change.

### Route planning wizard

- For planners the wizard's last step is now **Bikers**: only after the postal codes are settled does the split dialog (biker workloads, zip/district locks) appear, inline in the wizard, leading to the split review.
- **New Route is now a step-by-step wizard**: Upload → Geocode → Fix addresses → Optimize. Every step can be revisited with the stepper or Back/Next buttons; changing the picked files re-imports them into the same route.
- **Multiple files per route.** Pick or drop several `.csv`/`.xlsx`/`.txt`/`.xml` files; their stops are merged into one route (`POST /api/upload/` accepts repeated `file` fields, plus `session_id` to replace the stops of a not-yet-started route).
- **The planner dashboard's "Upload Route" and "Upload for <biker>" buttons now open the wizard** instead of importing the file straight onto the dashboard, so every upload goes through geocoding, address fixes and postal-code selection first.
- **Postal codes step.** After fixing addresses, the route's irányítószám groups are listed with stop counts. Tick/untick a code to include it in the day's plan (excluded stops are skipped by optimize and split), expand a code with the down arrow to see its addresses, untick single addresses, or move an address to another postal-code group (`POST /api/sessions/<id>/stops/bulk/`; new `postal_code` and `excluded` stop fields, backfilled by migration 0010).
- **Fix addresses window.** Stops the geocoder could not find are listed separately; the user rewrites the address and re-checks it (`PATCH /api/sessions/<id>/stops/<stop_id>/address/`). Planners can also remove a stop.

### Route navigation
- **Existing routes open in the wizard.** An unplanned route reopens at the step it needs (geocode, fix addresses or postal codes); an optimized one drops the biker on the map, with the earlier steps one click away in the stepper.
- **Back buttons.** A "Route planner" button on the map returns to the planning steps; bikers get a "My routes" button that returns to the list of all their routes without auto-reopening a lone active route.
- **Rename routes** from the map header, the biker route list and the dashboard (`RouteNameField`). The backend lets a route's owner rename it as well as planners.
- **Re-optimize is planner-only** once a route has a stop order, so a biker cannot overwrite the planner's order on an assigned route.

### Clustering
- **A split route is one card for the planner.** It sits in a "Split between bikers" column listing its sub-routes (biker, status, progress); clicking it opens the Bikers step of the wizard. The sub-route cards, the cluster banner and the split modal on the dashboard are gone. `GET /api/sessions/` returns top-level sessions with a `sub_routes` summary, and `?parent_id=<id>` lists the children.
- **Bikers only see their own sub-route.** Split parents are hidden from biker lists; each biker sees the part assigned to them.
- **Stop popup on the split-review map** shows which biker carries the stop, with **Stop details** (recipient, phone, position, estimated arrival, or delivered/not-received time) and **Move to…** (a window over the map to hand the stop to another biker). Stops now record `delivered_at` (migration 0011).
- The `uncluster/` and `move-stop/` backend endpoints are unchanged.

---

## Beta 1.0.1 (2026-04-10)

UX polish release addressing findings from the 2026-04-10 desktop and mobile usability reports. No new features -- existing flows were hardened for discoverability, consistency, and accident prevention.

### Feedback & Notifications
- **Toast notifications** for share-link creation, route rename, delete, assign/unassign, and undo-split (previously these actions succeeded silently)
- **Confirmation dialog** before **Undo Split** -- the destructive cascade no longer fires on a single click

### Navigation & Sign-out
- **Header user menu**: Help, Theme toggle, and Sign Out now live in a single kebab dropdown. The username button no longer logs you out on click -- Sign Out is an explicit dropdown item
- **Mobile header overflow**: below 380px the entire header toolbar collapses to a kebab menu so Sign Out can never get clipped off-screen (the LastMile wordmark is also hidden on ultra-narrow viewports)
- **Auto-select route on login**: bikers with exactly one in-progress route are dropped straight into that route's map view instead of the empty session list
- **Cross-user state reset**: logging out and back in as a different user no longer leaks the previous account's selected route, sidebar state, or dashboard view

### Biker Route View
- **Stop list sorted by sequence**: after optimization, the sidebar stop list is re-sorted to match the numbered map markers
- **Escape closes modals**: pressing `Esc` closes the StopDetail and Finished Route stats modals
- **Settings auto-opens sidebar**: tapping the gear while the mobile sidebar is collapsed now opens the sidebar so the settings panel is visible

### Planner Dashboard
- **Inline rename scroll**: the rename text field now scrolls to the beginning so long route names are visible from the start
- **Split button label**: the "Split into Routes" banner no longer shows a (frequently wrong) cluster count
- **Tablet kanban**: at 640-768px viewports (iPad portrait) the dashboard now shows 2 columns instead of collapsing to one

### Cluster Review
- **Compact Optimize All**: below 480px the button shows as "Optimize (N)" so the remaining-count stays visible

### Seed Data
- Test data now uses realistic Hungarian recipient names, phone numbers, and product codes

---

## Beta 1.0 (2026-04-08)

First public beta release. Full delivery planning workflow for bikers and planners.

### Core Features
- Multi-format file upload (CSV, XLSX, TXT, XML) with drag-and-drop
- Real-time geocoding via Nominatim with NDJSON streaming (pins appear one-by-one)
- Route optimization using VROOM algorithm (OpenRouteService)
- Road-following route geometry via ORS Directions API
- Interactive Leaflet map with numbered color-coded markers and auto-zoom
- Route sharing via public links (no login required)

### Authentication & Roles
- Token-based auth with username + role login (no passwords, demo app)
- Biker role: sees own routes, delivers stops, tracks progress
- Planner role: manages all routes, assigns to bikers, monitors live

### Planner Dashboard
- Kanban-style dashboard with drag-and-drop route assignment
- Biker columns with active/inactive/all filter
- Route cards showing status, progress, estimated return time
- Upload, rename, delete, assign routes from dashboard
- Finished routes section with delivery stats panel

### Bulk Clustering
- KMeans geographic clustering for large uploads (50+ stops)
- Auto-split oversized clusters to respect ORS 48-stop limit
- Parent/child session hierarchy (parent status = "split")
- Cluster review view with color-coded map and collapsible sub-route cards
- Move stops between sibling sub-routes
- Per-route optimize and assign from cluster review
- Optimize All button for batch optimization
- Undo split (blocked if any sub-route is in progress)
- Empty route warning and delete for sub-routes with all stops moved out
- Skipped stops indicator for non-geocoded stops

### Biker Route Execution
- Route lifecycle: not_started -> in_progress -> finished
- Stop status tracking: pending -> delivered / not_received / skipped
- Auto-advance to next pending stop after marking
- Auto-finish when all stops are marked
- Re-optimize in-progress routes with confirmation prompt
- Stop detail popup with arrival times, recipient info, tappable phone numbers

### Live Tracking
- Aggregate live map showing all active routes (planner only)
- 30-second auto-refresh polling
- Per-biker color coding with legend
- Current stop markers with biker initials
- Click-to-view-route from live map popups

### Mobile & UX
- Responsive design with mobile-optimized dashboard
- Centered columns (480px max-width) on mobile
- Touch-friendly buttons (32px targets), hidden drag handles
- Mobile back button for bikers in upload view
- Sidebar toggle for map view on mobile
- Dark/light theme with OS preference detection
- Settings panel: depot, start time, dwell time, travel speed

### Backend
- Django + DRF with 20 API endpoints
- SQLite database with indexed hot columns
- N+1 query elimination (annotated querysets)
- Production HTTPS enforcement (HSTS, SSL redirect, secure cookies)
- 10 MB file upload limit
- Geocoding logging with Nominatim diagnostics
- WhiteNoise static file serving for production

### Testing & CI
- Playwright E2E test suite: 9 spec files covering all major user journeys
- E2E mock mode (deterministic fake geocoding + optimization, no external API calls)
- GitHub Actions CI: backend lint + test, frontend lint + build, E2E on PRs
- Playwright report uploaded as artifact on failure

### Deployment
- Render free tier (auto-deploy from main branch)
- Django serves API + built React SPA via WhiteNoise
- SPA catch-all route for client-side routing

---

## New Features

_Future releases will be listed here. When adding a feature, add a new entry under the current version or create a new version section._
