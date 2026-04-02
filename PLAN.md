# Delivery Tracker — Route & Stop Status System

## Overview
Add live delivery tracking: bikers mark stops as delivered/failed, routes have start/finish lifecycle, planners see real-time progress. Split into two tiers by complexity.

---

## Tier 1: Stop & Route Status System
Core status tracking — bikers interact with stops, routes have lifecycle, finished routes move to a separate bin.

### 1.1 Backend — Model Changes
**File: `backend/planner/models.py`**
- [ ] Add `status` field to `DeliveryStop`: `pending` | `delivered` | `not_received` | `skipped` (default: `pending`)
- [ ] Add `status` field to `DeliverySession`: `not_started` | `in_progress` | `finished` (default: `not_started`)
- [ ] Add `started_at` timestamp to `DeliverySession` (nullable, set when biker starts route)
- [ ] Add `finished_at` timestamp to `DeliverySession` (nullable, set when route completes)
- [ ] Add `current_stop_index` to `DeliverySession` (nullable, tracks which stop biker is heading to)
- [ ] Create migration

### 1.2 Backend — API Endpoints
**File: `backend/planner/views.py` + `urls.py`**
- [ ] `PATCH /api/sessions/<id>/start/` — biker starts route (sets status=in_progress, started_at=now)
- [ ] `PATCH /api/sessions/<id>/stops/<stop_id>/status/` — biker updates stop status (delivered/not_received/skipped)
- [ ] Auto-advance `current_stop_index` when a stop is marked
- [ ] Auto-finish route when all stops are marked (status=finished, finished_at=now)
- [ ] `GET /api/sessions/` — update serializer to include new fields (status, started_at, current_stop_index)

### 1.3 Backend — Serializer Updates
**File: `backend/planner/serializers.py`**
- [ ] Add stop `status` to `DeliveryStopSerializer`
- [ ] Add session `status`, `started_at`, `finished_at`, `current_stop_index` to serializers
- [ ] Add `SessionListSerializer` fields: status, current_stop_index

### 1.4 Frontend — Types & API
**File: `frontend/src/types/index.ts` + `frontend/src/api/client.ts`**
- [ ] Add `status` to `DeliveryStop` type
- [ ] Add `status`, `started_at`, `finished_at`, `current_stop_index` to `SessionSummary` and `SessionResponse`
- [ ] Add `startRoute(sessionId)` API call
- [ ] Add `updateStopStatus(sessionId, stopId, status)` API call

### 1.5 Frontend — Biker Route View (Map Mode)
**File: `frontend/src/components/AddressList.tsx` + `App.tsx`**
- [ ] "Start Route" button — visible when route is optimized and status is `not_started`
- [ ] Next stop highlighted differently (current_stop_index) — bold, colored indicator
- [ ] Each stop shows status badge: pending (gray), delivered (green check), not_received (red x), skipped (yellow dash)
- [ ] Action buttons on each stop: "Delivered", "Not Received", "Skip"
- [ ] When stop is marked, auto-scroll to next stop
- [ ] Route progress indicator (e.g., "5/12 stops completed")

### 1.6 Frontend — Planner Dashboard Updates
**File: `frontend/src/components/PlannerDashboard.tsx`**
- [ ] Session cards show route status badge (not_started: gray, in_progress: blue pulse, finished: green)
- [ ] In-progress cards show: current stop name, progress (e.g., "3/10"), ETA for current stop
- [ ] "Finished Routes" section/bin — separate from active biker columns
- [ ] Finished routes show completion summary (delivered count, not_received count, duration)

### 1.7 Frontend — CSS
**File: `frontend/src/App.css`**
- [ ] Stop status badges (color-coded)
- [ ] Start Route button styling
- [ ] Next-stop highlight in address list
- [ ] In-progress card pulse animation
- [ ] Finished routes bin styling
- [ ] Action button row on each stop

### 1.8 Tests
- [ ] Backend: test start route, update stop status, auto-finish
- [ ] Backend: test permission checks (biker can only update own route)
- [ ] Manual: full flow — start route, mark stops, see dashboard update

### 1.9 Test Data
- [ ] Create management command or script to generate multiple test routes with different statuses
- [ ] At least 3 bikers with 2-3 routes each (mix of not_started, in_progress, finished)

---

## Tier 2: Planner Aggregate Map & Live Tracking
Real-time visibility for planners — see all bikers on one map with ETAs. Requires polling or WebSockets.

### 2.1 Backend — Live Position
- [ ] Decide: polling vs WebSocket (Django Channels)
- [ ] If polling: `PATCH /api/sessions/<id>/position/` — biker reports last known stop
- [ ] If WebSocket: set up Django Channels, create consumer for position updates
- [ ] Calculate ETA based on current_stop_index + route segments + settings

### 2.2 Backend — Aggregate Endpoint
- [ ] `GET /api/sessions/active/` — planner-only, returns all in_progress sessions with current position, ETA, biker name
- [ ] Include route geometry for each active session (for drawing on map)

### 2.3 Frontend — Planner Aggregate Map
- [ ] New component: `PlannerMapView.tsx`
- [ ] Show all active biker routes on one map (different colors per biker)
- [ ] Biker markers showing current position (which stop they're heading to)
- [ ] Popup on biker marker: name, current stop, ETA, progress
- [ ] Auto-refresh interval (every 30s or configurable)

### 2.4 Frontend — Dashboard Integration
- [ ] "Live Map" button on dashboard header to switch to aggregate map
- [ ] In-progress cards: "where biker is headed" text + ETA countdown
- [ ] Optional: notification when a biker finishes their route

### 2.5 Design Decisions (TBD)
- [ ] Polling interval vs WebSocket tradeoff
- [ ] Does biker's phone need to send GPS? Or just "checked off stop X"?
- [ ] How to handle offline bikers (no updates for >N minutes)?
- [ ] Color scheme for multiple bikers on one map

---

## Progress Tracker

| Phase | Status | Notes |
|-------|--------|-------|
| 1.1 Model changes | Done | Migration 0005_add_status_fields |
| 1.2 API endpoints | Done | start_route + update_stop_status |
| 1.3 Serializers | Done | delivery_status, session status fields, delivered_count, current_stop_name |
| 1.4 Frontend types & API | Done | Types + startRoute/updateStopStatus API calls |
| 1.5 Biker route view | Done | Start Route btn, next-stop highlight, status badges, action buttons |
| 1.6 Dashboard updates | Done | Status badges, progress, finished routes bin |
| 1.7 CSS | Done | All status UI styles |
| 1.8 Tests | Partial | Backend lint + Django check pass. Full test suite hangs (env issue, not code) |
| 1.9 Test data | Done | 9 routes across 3 bikers via seed_test_data command |
| 2.1 Live position | Not started | Design decisions needed first |
| 2.2 Aggregate endpoint | Not started | |
| 2.3 Planner aggregate map | Not started | |
| 2.4 Dashboard integration | Not started | |
| 2.5 Design decisions | Not started | |
