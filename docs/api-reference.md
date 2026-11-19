# API Reference

> **Beta 1.0** -- 20 endpoints

**Base URL:**
- Local development: `http://localhost:8000/api/`
- Production: `https://lastmile-c07a.onrender.com/api/`

All authenticated endpoints require the header: `Authorization: Token <token>`

## Authentication

### POST /auth/login/

Create or retrieve a user account and get a token.

**Request:**
```json
{ "username": "anna", "role": "biker" }
```

**Response** `200`:
```json
{
  "token": "abc123...",
  "user": { "id": 1, "username": "anna", "role": "biker" }
}
```

Role must be `"biker"` or `"planner"`. If the username doesn't exist, it is created automatically.

### GET /auth/me/

Returns the current user's profile.

**Response** `200`:
```json
{ "id": 1, "username": "anna", "role": "biker" }
```

### POST /auth/logout/

Deletes the user's token. No request body needed.

---

## Sessions (Routes)

### POST /upload/

Upload a file to create a new session. Send as `multipart/form-data`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | CSV, XLSX, TXT, or XML file |
| `owner_id` | integer | No | Assign to a biker (planner only) |

**Response** `201`:
```json
{
  "id": "uuid",
  "name": "Monday Deliveries",
  "status": "not_started",
  "stops": [ ... ],
  "needs_geocoding": true
}
```

### GET /sessions/

List sessions. Bikers see their own routes; planners see all.

Query parameters:
- `owner_id` -- filter by biker (planner only)

**Response** `200`:
```json
[
  {
    "id": "uuid",
    "name": "Monday Deliveries",
    "status": "in_progress",
    "stop_count": 10,
    "delivered_count": 4,
    "not_received_count": 1,
    "current_stop_name": "Pizza King",
    "created_at": "2026-04-02T10:00:00Z"
  }
]
```

### GET /sessions/{id}/

Get full session details including all stops, route geometry, and segments.

### DELETE /sessions/{id}/delete/

Delete a session and all its stops. Planner only.

### PATCH /sessions/{id}/assign/

Assign or unassign a session. Planner only.

**Assign to a biker:**
```json
{ "owner_id": 3 }
```

**Unassign (remove from biker):**
```json
{ "owner_id": null }
```

### PATCH /sessions/{id}/rename/

Rename a session. Planner only.

**Request:**
```json
{ "name": "Downtown Run" }
```

---

## Geocoding

### POST /sessions/{id}/geocode/

Geocode all pending stops. Returns a stream of NDJSON (one JSON object per line).

Stops go through the address pipeline, `GEOCODE_CONCURRENCY` (default 5) requests at a time: identical addresses are
looked up once and reused from earlier results (`cache`); the address as written (`raw`); failures are cleaned by the
rule-based Hungarian parser (birth dates, phones, notes, abbreviations, missing zip/city, misspelled street) and
retried (`parsed`); then Google, only when `GOOGLE_GEOCODING_API_KEY` is set (`google`); what is still missing is
`failed` with `geocode_stage: "manual"` and suggested addresses. A hit that disagrees with the address's postal code or
settlement is never accepted. See `docs/backlog/address-pipeline.md`.

Each streamed `stop` also carries `geocode_stage`, `cleaned_address`, `parsed_parts`
(`zip, city, district, street, house, unit, removed[], steps[], confidence`) and `address_candidates` (best first).

**Response** `200` (streamed):
```
{"stop": {"id": 2, "name": "Pizza King", "lat": 47.4965, "lng": 19.0565, "geocode_status": "success"}, "progress": {"current": 1, "total": 9}}
{"stop": {"id": 3, "name": "Spar Blaha", "lat": 47.4963, "lng": 19.0696, "geocode_status": "success"}, "progress": {"current": 2, "total": 9}}
```

### PATCH /sessions/{id}/stops/{stop_id}/address/

Replace a stop's address and re-geocode it through the same pipeline (`geocode_stage` is `manual` when the typed
address was found directly). Body: `{"address": "..."}`.

### GET /sessions/{id}/geocode-status/

Check geocoding progress without streaming.

---

## Route Optimization

### POST /sessions/{id}/optimize/

Optimize the stop order and generate route geometry. Can be called on routes in any status -- for in-progress routes, this re-optimizes the remaining stops.

**Request** (optional):
```json
{ "depot_lat": 47.5003, "depot_lng": 19.0841 }
```

Depot coordinates are optional. If omitted, the route is optimized without a fixed start/end point.

**Response** `200`:
```json
{
  "optimized_stops": [ ... ],
  "route_geometry": { "type": "LineString", "coordinates": [...] },
  "route_segments": [{ "duration": 120, "distance": 1500 }, ...],
  "total_duration": 3600,
  "total_distance": 25000
}
```

---

## Bulk Clustering

### POST /sessions/{id}/cluster/

Split a session's geocoded stops into N sub-routes. **A postal code is never split:** all stops sharing a `postal_code` go to the same sub-route (largest zips first, each to the nearest route with room). Planner only. The parent session's status becomes `split` and its stops are moved to child sessions.

**Request** (all fields optional):
```json
{ "n_routes": 7, "max_stops_per_route": 48 }
```

If `n_routes` is omitted, it is auto-calculated from the stop count and `max_stops_per_route` (default 48, which is the ORS optimization limit).

Alternatively pass `assignments` for a planned split (used by the Split Planner UI). Each entry names a biker, an approximate stop count, and optionally a Budapest district (1-23) the biker is locked to:

```json
{
  "assignments": [
    { "biker_id": 3, "target_stops": 40, "district": null },
    { "biker_id": 4, "target_stops": 20, "district": 13 }
  ]
}
```

Zip-locked bikers receive every stop of that postal code, district-locked bikers every stop in their district (zip locks win); the remaining zips are distributed with sizes proportional to `target_stops`, never splitting a zip. Each sub-route is created with its biker as owner. If every assignment is district-locked, leftover stops go into an extra unassigned sub-route.

**Response** `201`:
```json
{
  "parent_id": "uuid",
  "sub_routes": [
    { "id": "uuid", "name": "Monday Deliveries - Route 1", "stop_count": 43, "owner_id": 3, "owner_name": "anna" },
    { "id": "uuid", "name": "Monday Deliveries - Route 2", "stop_count": 41, "owner_id": null, "owner_name": null }
  ],
  "oversized_zips": [{ "zip": "1054", "stop_count": 56 }],
  "unassigned_zones": [],
  "unzipped_stop_ids": [],
  "zip_conflicts": [],
  "cluster_summary": {
    "total_stops": 284,
    "skipped_stops": 16,
    "n_routes": 7,
    "avg_stops_per_route": 40.6,
    "min_stops": 35,
    "max_stops": 48
  }
}
```

`oversized_zips` lists zips larger than `max_stops_per_route` (kept whole on one route). `unzipped_stop_ids` lists stops without a postal code (grouped onto the smallest route; if no stop has a zip, a geographic split is used). `zip_conflicts` is explained under `move-stop` below and is empty right after a split.

**Zone-first allocation.** When every assignment carries `window_minutes` (the biker's available time) and none is locked to a `zip`/`district`, whole zones are handed to bikers by estimated load (stops x service time x optional `multiplier`, plus a heuristic travel estimate and a break) up to `window_minutes` itself (the 7.5 % overrun is not a planning target; see below). Each sub-route then also has `load_minutes`, `capacity_minutes` (= the window) and `zones`. A zone that fits nowhere is listed in `unassigned_zones` (`{zone, stop_count, load_minutes}`); its stops are still placed (see next paragraph) so none are lost. `window_minutes` must be given for every biker or for none, and cannot be combined with a `zip`/`district` lock (400 otherwise). A biker the windows do not need gets no empty route; they are listed in `unused_bikers` (usernames). Without `window_minutes` the behaviour is unchanged. The web wizard does not send `window_minutes` yet (backlog B1): today only API callers reach this path.

**Managing zones.** `GET /api/zones/` lists zones (`{id, name, zips}`); `POST /api/zones/` `{name, zips}` adds one (id is assigned, `Z17`, ...); `PUT /api/zones/<id>/` replaces name and zips; `DELETE /api/zones/<id>/` removes it (its postal codes are then planned on their own). Planner only. A postal code is 4 digits starting with 1 and may belong to one zone; violations return 400 naming the code. Edits apply to the next split.

**Breaking zones (fallback).** Zones that fit no biker whole (`unassigned_zones`) are then placed zip by zip, breaking as few zones as possible. Cost order: minutes beyond the 7.5 % tolerance, minutes beyond the window, zones broken, total load; so the tolerance is used only as overflow, and such a route has `uses_overrun: true`. The search is branch-and-bound and provably optimal within a node budget; `split_exact: false` means the budget ran out and the best plan found is returned. The response adds `split_zones` (`[{zone_id, parts: [{zips, route}]}]`, `route` = sub-route name) and `over_capacity_zips`; a sub-route that still exceeds its window (e.g. one zip bigger than any window, kept whole) has `over_capacity: true`. `GET /api/sessions/<id>/` of a split route also returns `split_zones`, computed from the routes as they are now.

Stops that are not geocoded (`geocode_status` != `success` and no lat/lng) are skipped and remain on the parent session.

### GET /sessions/{id}/districts/

City districts present in a session's geocoded stops, for the Split Planner. Districts are parsed from Budapest postal codes (`1052` → district 5). Planner only.

**Response** `200`:
```json
{
  "districts": [
    { "district": 5, "label": "V. kerület", "stop_count": 20 },
    { "district": 13, "label": "XIII. kerület", "stop_count": 10 }
  ],
  "unknown_district_stops": 3,
  "total_stops": 33
}
```

### DELETE /sessions/{id}/stops/{stop_id}/remove/

Remove a single stop from a route (used during split review). Clears the session's cached route geometry/duration so it can be re-optimized. Planner only; fails with `400` if the route is `in_progress`.

**Response** `200`:
```json
{ "removed_stop_id": 123, "remaining_stops": 42 }
```

### POST /sessions/{id}/move-stop/

Move a stop from one sub-route to a sibling sub-route (both must share the same parent). Planner only.

**Request:**
```json
{ "stop_id": 123, "to_session_id": "uuid" }
```

**Response** `200`:
```json
{
  "stop_id": 123,
  "from_session_id": "uuid",
  "to_session_id": "uuid",
  "from_count": 42,
  "to_count": 44,
  "zip_conflicts": [
    {
      "zip": "1082",
      "zone": "Z12",
      "routes": [
        { "session_id": "uuid", "name": "Day_1", "count": 4 },
        { "session_id": "uuid", "name": "Day_2", "count": 2 }
      ]
    }
  ]
}
```

`zip_conflicts` lists postal codes now spread over more than one sub-route of the parent (excluded stops and stops without a zip are ignored). It is informational and never blocks moving, optimizing or saving. The same field is returned by `GET /sessions/{id}/` for a split parent (`[]` otherwise)

### POST /sessions/{id}/move-zip/

Move every stop of one postal code (or a whole zone) into one sub-route of a split session. `{id}` is the **parent** session. Planner only. Send exactly one of `zip` or `zone_id`. Excluded stops stay where they are. Every route that lost or gained stops loses its stop order, geometry and duration (re-optimize it). All-or-nothing.

**Request:**
```json
{ "zip": "1082", "to_session_id": "uuid" }
```

**Response** `200`: `moved_count`, `moved_zips`, `to_session_id`, `counts` (stop count per sub-route id) and `zip_conflicts` (as in `move-stop`).

**Errors** `400`: both or neither of `zip`/`zone_id`, unknown zone, no stops with that zip, parent not split, or any route involved is `in_progress`/`finished`. `404`: target is not a sub-route of this session. `403`: not a planner.

### DELETE /sessions/{id}/uncluster/

Undo a cluster split. Deletes all sub-routes, restores stops to the parent session, and resets the parent status to `not_started`. Planner only.

Fails with `409 Conflict` if any sub-route has status `in_progress` (a biker is actively delivering).

**Response** `200`:
```json
{
  "message": "Split undone successfully",
  "session_id": "uuid",
  "stops_restored": 284,
  "sub_routes_deleted": 7
}
```

---

## Delivery Tracking

### PATCH /sessions/{id}/start/

Start a route. Sets status to `in_progress` and marks the first stop as current.

**Response** `200`:
```json
{
  "status": "in_progress",
  "current_stop_index": 0,
  "started_at": "2026-04-02T09:00:00Z"
}
```

### PATCH /sessions/{id}/stops/{stop_id}/status/

Mark a stop's delivery status.

**Request:**
```json
{ "delivery_status": "delivered" }
```

Values: `delivered`, `not_received`, `skipped`

**Response** `200`:
```json
{
  "stop": { "id": 5, "delivery_status": "delivered", ... },
  "session_status": "in_progress",
  "current_stop_index": 3
}
```

When all stops are marked, `session_status` becomes `"finished"`.

### GET /sessions/active/

List all in-progress sessions with full stop data. Planner only. Used by the live map.

---

## Sharing

### POST /sessions/{id}/share/

Create a public share link for a route.

**Response** `200`:
```json
{ "share_id": "uuid" }
```

### GET /shared/{share_id}/

Get a shared route. No authentication required.

---

## Users

### GET /users/bikers/

List all users with the biker role. Planner only.

**Response** `200`:
```json
[
  { "id": 1, "username": "anna" },
  { "id": 2, "username": "balazs" }
]
```
