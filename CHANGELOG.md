# Changelog

All notable changes to LastMile are documented here.

Format: features are grouped by category. Each version includes a release date and summary.

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
