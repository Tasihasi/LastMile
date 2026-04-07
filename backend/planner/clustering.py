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


def calculate_n_clusters(stop_count, max_stops_per_cluster=48):
    """Calculate the minimum number of clusters needed."""
    if stop_count <= 0:
        return 0
    return math.ceil(stop_count / max_stops_per_cluster)
