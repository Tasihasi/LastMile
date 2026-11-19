"""Offline tour optimizer: nearest-neighbour start + 2-opt improvement on great-circle distances.

Used where ORS is not available (E2E mock mode) and by the time model's travel estimate, so that
"optimized" always means a short closed tour, never an angle sort or an arbitrary order.
"""

from .budapest import haversine_km


def tour_length(order, dist):
    """Closed tour length for `order` (indices >=1) starting and ending at node 0."""
    path = [0, *order, 0]
    return sum(dist[a][b] for a, b in zip(path, path[1:], strict=False))


def optimize_order(points, depot=None):
    """Return indices into `points` in a short visiting order (closed tour via depot).

    Without a depot the tour starts/ends at points[0], like the ORS call does.
    Deterministic: ties break on the lowest index.
    """
    n = len(points)
    if n < 2:
        return list(range(n))

    nodes = [depot, *points] if depot else list(points)
    dist = [[haversine_km(a, b) for b in nodes] for a in nodes]

    # nearest neighbour from node 0 (the depot, or the first point)
    unvisited = set(range(1, len(nodes)))
    order, cur = [], 0
    while unvisited:
        nxt = min(unvisited, key=lambda j: (dist[cur][j], j))
        order.append(nxt)
        unvisited.discard(nxt)
        cur = nxt

    # 2-opt: reverse segments while that shortens the closed tour
    improved = True
    while improved:
        improved = False
        path = [0, *order, 0]
        for i in range(1, len(path) - 2):
            for j in range(i + 1, len(path) - 1):
                delta = (
                    dist[path[i - 1]][path[j]]
                    + dist[path[i]][path[j + 1]]
                    - dist[path[i - 1]][path[i]]
                    - dist[path[j]][path[j + 1]]
                )
                if delta < -1e-9:
                    path[i : j + 1] = reversed(path[i : j + 1])
                    improved = True
        order = path[1:-1]

    return [k - 1 for k in order] if depot else [0, *order]
