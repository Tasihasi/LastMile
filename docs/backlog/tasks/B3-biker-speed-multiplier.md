# B3 — Per-biker service-time multiplier

**Email §2 (secondary, later)** · **P2** · **Depends on:** B1 · **Size:** S

Courier profile gets a multiplier applied to the base per-address time: normal 1.0 (2 min), trainee 2.0 (4 min), fast 0.85 (1.7 min).

## Scope
- `UserProfile.service_time_multiplier` (`FloatField`, default 1.0, validators 0.3–5.0), migration.
- Exposed in `GET /api/users/bikers/`; editable by planner via `PATCH /api/users/bikers/<id>/` (new, planner-only) or Django admin at minimum.
- `estimate_route_minutes` (B2) and allocation (A5) read it.

## Acceptance criteria
- **B3-AC1** Default 1.0 for existing and new bikers (migration data-safe).
- **B3-AC2** Values outside 0.3–5.0 rejected (400).
- **B3-AC3** Route with 30 stops, base 2 min: multiplier 2.0 adds exactly 30 more minutes than 1.0 in `estimated_minutes`.
- **B3-AC4** Only planners can edit; biker editing own multiplier → 403.
- **B3-AC5** Bikers list endpoint returns the field.

## Test plan
- U: AC3 via `estimate_route_minutes`.
- A: AC1, AC2, AC4, AC5.
- Migration check: `makemigrations --check`.
