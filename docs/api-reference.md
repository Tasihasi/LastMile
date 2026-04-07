# API Reference

Base URL: `http://localhost:8000/api/`

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

**Response** `200` (streamed):
```
{"stop": {"id": 2, "name": "Pizza King", "lat": 47.4965, "lng": 19.0565, "geocode_status": "success"}, "progress": {"current": 1, "total": 9}}
{"stop": {"id": 3, "name": "Spar Blaha", "lat": 47.4963, "lng": 19.0696, "geocode_status": "success"}, "progress": {"current": 2, "total": 9}}
```

### GET /sessions/{id}/geocode-status/

Check geocoding progress without streaming.

---

## Route Optimization

### POST /sessions/{id}/optimize/

Optimize the stop order and generate route geometry.

**Request** (optional):
```json
{ "depot": { "lat": 47.5003, "lng": 19.0841 } }
```

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

Cluster a session's geocoded stops into N geographic sub-routes using KMeans. Planner only. The parent session's status becomes `split` and its stops are moved to child sessions.

**Request** (all fields optional):
```json
{ "n_routes": 7, "max_stops_per_route": 48 }
```

If `n_routes` is omitted, it is auto-calculated from the stop count and `max_stops_per_route` (default 48, which is the ORS optimization limit).

**Response** `201`:
```json
{
  "parent_id": "uuid",
  "sub_routes": [
    { "id": "uuid", "name": "Monday Deliveries - Route 1", "stop_count": 43 },
    { "id": "uuid", "name": "Monday Deliveries - Route 2", "stop_count": 41 }
  ],
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

Stops that are not geocoded (`geocode_status` != `success` and no lat/lng) are skipped and remain on the parent session.

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
  "to_count": 44
}
```

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
