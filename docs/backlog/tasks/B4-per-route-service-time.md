# B4 — Per-route service-time override

**Email §2 (secondary, later)** · **P2** · **Depends on:** B1 · **Size:** S

Planner can edit the time spent per address for one specific route (district V = office buildings, quick hand-off; VI–VII = walk-ups, slower).

## Scope
- `DeliverySession.service_time_override_min` (`FloatField`, null → use global from `timing.py`), migration.
- Included in `rename`-like PATCH endpoint (or new `PATCH /api/sessions/<id>/timing/`), planner-only, only while `not_started`.
- UI: small editable field on the route card/wizard; shows effective value.
- Effective value precedence: route override > global; multiplier (B3) then applies on top.

## Acceptance criteria
- **B4-AC1** Null override → estimates identical to B2 behaviour.
- **B4-AC2** Override 3.0 on a route → `estimated_minutes` reflects 3.0 min/stop × multiplier.
- **B4-AC3** Override affects only that route; siblings unchanged.
- **B4-AC4** Values ≤ 0 or > 30 → 400.
- **B4-AC5** Editing an `in_progress`/`finished` route → 400; biker → 403.

## Test plan
- U: precedence helper — AC1, AC2.
- A: AC3, AC4, AC5.
- E: edit the field in UI, estimate badge (B2) updates.
