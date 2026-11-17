import math

import numpy as np
from sklearn.cluster import KMeans

from .districts import extract_postal_code


def cluster_stops(stops, n_clusters, max_stops_per_cluster=48, random_state=42):
    """
    Cluster geocoded stops into n geographic groups using KMeans.

    Args:
        stops: list of DeliveryStop with lat/lng (must be geocoded)
        n_clusters: number of clusters to create
        max_stops_per_cluster: hard cap per cluster (default 48 for ORS limit)
        random_state: seed for reproducibility

    Returns:
        list of lists -- stops grouped by cluster
        e.g., [[stop1, stop5, ...], [stop2, stop8, ...], ...]
    """
    if not stops:
        return []

    if n_clusters <= 0:
        n_clusters = 1

    # Cap n_clusters to the number of stops
    n_clusters = min(n_clusters, len(stops))

    coords = np.array([[s.lat, s.lng] for s in stops])
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    labels = kmeans.fit_predict(coords)

    clusters = [[] for _ in range(n_clusters)]
    for stop, label in zip(stops, labels, strict=True):
        clusters[label].append(stop)

    # Post-process: split any cluster that exceeds max_stops_per_cluster
    clusters = _enforce_max_size(clusters, max_stops_per_cluster)

    return clusters


def _enforce_max_size(clusters, max_size):
    """
    If any cluster exceeds max_size, split it by re-running KMeans on that cluster.
    Repeats until all clusters are within the limit.
    """
    result = []
    for cluster in clusters:
        if len(cluster) <= max_size:
            result.append(cluster)
        else:
            # Split oversized cluster into ceil(len/max_size) sub-clusters
            n_sub = math.ceil(len(cluster) / max_size)
            coords = np.array([[s.lat, s.lng] for s in cluster])
            sub_kmeans = KMeans(n_clusters=n_sub, random_state=42, n_init=10)
            sub_labels = sub_kmeans.fit_predict(coords)

            sub_clusters = [[] for _ in range(n_sub)]
            for stop, label in zip(cluster, sub_labels, strict=True):
                sub_clusters[label].append(stop)

            # Recurse in case sub-clusters are still too large
            result.extend(_enforce_max_size(sub_clusters, max_size))

    return result


def cluster_stops_weighted(stops, target_counts, random_state=42):
    """
    Cluster stops into len(target_counts) geographic groups whose sizes match
    target_counts (which must sum to len(stops)).

    Runs KMeans to find geographic centers, pairs the largest natural cluster
    with the largest target, then greedily assigns each stop to the nearest
    center that still has capacity — keeping groups geographically compact
    while honouring the requested sizes.

    Returns a list of stop-lists, index-aligned with target_counts.
    """
    if not stops:
        return [[] for _ in target_counts]
    if len(target_counts) == 1:
        return [list(stops)]

    coords = np.array([[s.lat, s.lng] for s in stops])
    n_groups = len(target_counts)
    kmeans = KMeans(n_clusters=min(n_groups, len(stops)), random_state=random_state, n_init=10)
    labels = kmeans.fit_predict(coords)
    centers = kmeans.cluster_centers_

    # Pair natural cluster sizes with targets: biggest cluster -> biggest target,
    # so a half-day biker gets a smaller (but still compact) area.
    natural_sizes = np.bincount(labels, minlength=len(centers))
    clusters_by_size = np.argsort(-natural_sizes)  # center indices, largest first
    targets_by_size = sorted(range(n_groups), key=lambda i: -target_counts[i])

    # target index -> center coords (extra targets beyond available centers
    # reuse the last center; only happens when stops < groups)
    target_centers = np.zeros((n_groups, 2))
    for rank, target_idx in enumerate(targets_by_size):
        center_idx = clusters_by_size[min(rank, len(centers) - 1)]
        target_centers[target_idx] = centers[center_idx]

    # Greedy assignment: closest (stop, center) pairs first, respecting capacity.
    distances = np.linalg.norm(coords[:, None, :] - target_centers[None, :, :], axis=2)
    order = np.dstack(np.unravel_index(np.argsort(distances, axis=None), distances.shape))[0]

    remaining = list(target_counts)
    assigned = [None] * len(stops)
    n_assigned = 0
    for stop_idx, target_idx in order:
        if assigned[stop_idx] is not None or remaining[target_idx] <= 0:
            continue
        assigned[stop_idx] = target_idx
        remaining[target_idx] -= 1
        n_assigned += 1
        if n_assigned == len(stops):
            break

    groups = [[] for _ in target_counts]
    for stop, target_idx in zip(stops, assigned, strict=True):
        if target_idx is None:
            # capacities under-count due to rounding; put extras in the largest group
            target_idx = targets_by_size[0]
        groups[target_idx].append(stop)
    return groups


def split_counts(total, weights):
    """
    Split `total` into integer counts proportional to `weights` (largest
    remainder method). Every entry with a positive weight gets at least the
    rounded share; counts always sum to total.
    """
    if total <= 0 or not weights:
        return [0] * len(weights)
    weight_sum = sum(weights)
    if weight_sum <= 0:
        weights = [1] * len(weights)
        weight_sum = len(weights)

    raw = [total * w / weight_sum for w in weights]
    counts = [int(r) for r in raw]
    shortfall = total - sum(counts)
    remainders = sorted(range(len(raw)), key=lambda i: raw[i] - counts[i], reverse=True)
    for i in remainders[:shortfall]:
        counts[i] += 1
    return counts


def calculate_n_clusters(stop_count, max_stops_per_cluster=48):
    """Calculate the minimum number of clusters needed."""
    if stop_count <= 0:
        return 0
    return math.ceil(stop_count / max_stops_per_cluster)


def stop_zip(stop):
    """Postal code of a stop ("" if unknown): the stored field, else parsed from the address."""
    return (getattr(stop, "postal_code", "") or "").strip() or extract_postal_code(stop.raw_address)


class ZipAtomicResult:
    """Outcome of cluster_zip_atomic.

    clusters:       list index-aligned with the requested targets (may contain empty lists).
    oversized_zips: [{"zip": str, "stop_count": int}] for zips larger than max_stops (kept whole).
    unzipped_stops: stops without a postal code (bucketed into the smallest route).
    """

    def __init__(self, clusters, oversized_zips, unzipped_stops):
        self.clusters = clusters
        self.oversized_zips = oversized_zips
        self.unzipped_stops = unzipped_stops


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def cluster_zip_atomic(stops, n_routes=None, targets=None, max_stops=48):
    """Distribute geocoded stops over routes so that no postal code is ever split.

    All stops sharing a zip form one indivisible group. Groups are placed largest-first
    (greedy LPT): the biggest groups seed one route each, then every group goes to the
    nearest route (by weighted centroid) that still has room under its target; if no route
    has room, to the route with the most spare capacity. Stops without a zip are bucketed
    together and added last to the smallest route.

    Give either `targets` (desired stop count per route, index-aligned result) or
    `n_routes` (equal targets). Deterministic for identical input.

    If no stop has a zip at all, falls back to geographic weighted KMeans.
    """
    stops = list(stops)
    if targets is None:
        n = max(int(n_routes or 1), 1)
        targets = split_counts(len(stops), [1] * n)
    targets = list(targets)
    k = len(targets)
    if k == 0:
        raise ValueError("Need at least one route.")

    by_zip = {}
    unzipped = []
    for stop in stops:
        z = stop_zip(stop)
        if z:
            by_zip.setdefault(z, []).append(stop)
        else:
            unzipped.append(stop)

    if not by_zip:
        # Nothing to keep atomic (no stop has a postal code): plain geographic split.
        return ZipAtomicResult(cluster_stops_weighted(unzipped, targets), [], unzipped)

    def centroid(group):
        return (sum(s.lat for s in group) / len(group), sum(s.lng for s in group) / len(group))

    groups = sorted(by_zip.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    oversized = [{"zip": z, "stop_count": len(g)} for z, g in groups if len(g) > max_stops]

    clusters = [[] for _ in range(k)]
    centers = [None] * k  # weighted centroid per route

    def place(group, idx):
        gc = centroid(group)
        n_old = len(clusters[idx])
        if n_old:
            w = len(group) / (n_old + len(group))
            centers[idx] = (centers[idx][0] * (1 - w) + gc[0] * w, centers[idx][1] * (1 - w) + gc[1] * w)
        else:
            centers[idx] = gc
        clusters[idx].extend(group)

    # Routes with a zero target stay empty (unless every target is zero).
    active = [i for i in range(k) if targets[i] > 0] or list(range(k))

    # Seed: largest groups to the routes with the largest targets, one per route.
    seed_order = sorted(active, key=lambda i: (-targets[i], i))
    seeded = groups[: len(seed_order)]
    for (_, group), idx in zip(seeded, seed_order, strict=False):
        place(group, idx)

    for _, group in groups[len(seeded) :]:
        size = len(group)
        fitting = [i for i in active if len(clusters[i]) + size <= targets[i]]
        if fitting:
            gc = centroid(group)
            idx = min(fitting, key=lambda i: (_dist(gc, centers[i]), i))
        else:
            idx = max(active, key=lambda i: (targets[i] - len(clusters[i]), -i))
        place(group, idx)

    if unzipped:
        idx = min(active, key=lambda i: (len(clusters[i]), i))
        clusters[idx].extend(unzipped)

    return ZipAtomicResult(clusters, oversized, unzipped)
