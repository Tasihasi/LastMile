import math

import numpy as np
from sklearn.cluster import KMeans


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
