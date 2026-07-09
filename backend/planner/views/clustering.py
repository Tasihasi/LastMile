from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..clustering import calculate_n_clusters, cluster_stops, cluster_stops_weighted, split_counts
from ..districts import district_label, extract_district
from ..models import DeliverySession, DeliveryStop
from .helpers import require_planner


def _parse_assignments(raw):
    """Validate the split-planner assignments payload.

    Each item: {"biker_id": int|null, "target_stops": int, "district": int|null}.
    Returns (parsed_list, error_message).
    """
    if not isinstance(raw, list) or not raw:
        return None, "assignments must be a non-empty list."

    parsed = []
    for item in raw:
        if not isinstance(item, dict):
            return None, "Each assignment must be an object."

        owner = None
        biker_id = item.get("biker_id")
        if biker_id is not None:
            try:
                owner = User.objects.get(id=int(biker_id), profile__role="biker")
            except (User.DoesNotExist, ValueError, TypeError):
                return None, f"Biker {biker_id} not found."

        try:
            target = max(int(item.get("target_stops") or 0), 0)
        except (ValueError, TypeError):
            return None, "target_stops must be a number."

        district = item.get("district")
        if district is not None:
            try:
                district = int(district)
            except (ValueError, TypeError):
                return None, "district must be a number."
            if not 1 <= district <= 23:
                return None, "district must be between 1 and 23."

        parsed.append({"owner": owner, "target_stops": target, "district": district})
    return parsed, None


def _build_assignment_clusters(geocoded_stops, assignments):
    """Distribute stops across assignments honouring district locks and targets.

    Returns (clusters, leftover) where clusters is index-aligned with
    assignments and leftover holds stops no assignment can take (only when
    every assignment is district-locked).
    """
    pool = list(geocoded_stops)
    clusters = [[] for _ in assignments]

    # District-locked bikers take every stop in their district.
    district_groups = {}
    for i, a in enumerate(assignments):
        if a["district"] is not None:
            district_groups.setdefault(a["district"], []).append(i)

    for district, idxs in district_groups.items():
        district_stops = [s for s in pool if extract_district(s.raw_address) == district]
        pool = [s for s in pool if extract_district(s.raw_address) != district]
        if len(idxs) == 1:
            clusters[idxs[0]] = district_stops
        else:
            weights = [assignments[i]["target_stops"] for i in idxs]
            counts = split_counts(len(district_stops), weights)
            for i, group in zip(idxs, cluster_stops_weighted(district_stops, counts), strict=True):
                clusters[i] = group

    free_idxs = [i for i, a in enumerate(assignments) if a["district"] is None]
    if not free_idxs:
        return clusters, pool

    weights = [assignments[i]["target_stops"] for i in free_idxs]
    counts = split_counts(len(pool), weights)
    for i, group in zip(free_idxs, cluster_stops_weighted(pool, counts), strict=True):
        clusters[i] = group
    return clusters, []


@api_view(["POST"])
@transaction.atomic
def cluster_session(request, session_id):
    """Split a large session into clustered sub-routes using KMeans."""
    if not require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    # Lock the session row to prevent concurrent clustering of the same session
    try:
        session = DeliverySession.objects.select_for_update().get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    if session.sub_routes.exists():
        return Response(
            {"error": "Session already has sub-routes. Delete them first to re-cluster."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if session.parent is not None:
        return Response(
            {"error": "Cannot cluster a sub-route. Cluster the parent session instead."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    geocoded_stops = list(
        session.stops.filter(geocode_status__in=["success", "skipped"], lat__isnull=False, lng__isnull=False)
    )
    skipped_count = session.stops.exclude(geocode_status__in=["success", "skipped"]).count()

    if len(geocoded_stops) < 2:
        return Response(
            {"error": "Need at least 2 geocoded stops to cluster."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    assignments_raw = request.data.get("assignments")
    if assignments_raw is not None:
        assignments, err = _parse_assignments(assignments_raw)
        if err:
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)
        clusters, leftover = _build_assignment_clusters(geocoded_stops, assignments)
        owners = [a["owner"] for a in assignments]
        if leftover:
            # Every assignment was district-locked; keep the rest reviewable.
            clusters.append(leftover)
            owners.append(None)
    else:
        max_stops = int(request.data.get("max_stops_per_route", 48))
        n_routes_param = request.data.get("n_routes")
        n_routes = (
            int(n_routes_param) if n_routes_param is not None else calculate_n_clusters(len(geocoded_stops), max_stops)
        )
        clusters = cluster_stops(geocoded_stops, n_routes, max_stops_per_cluster=max_stops)
        owners = [None] * len(clusters)

    sub_routes = []
    for i, (cluster, owner) in enumerate(zip(clusters, owners, strict=True), start=1):
        child = DeliverySession.objects.create(
            parent=session,
            owner=owner,
            name=f"{(session.name or 'Route')[:248]}_{i}",
            original_file=session.original_file,
        )

        child_stops = []
        for stop in cluster:
            child_stops.append(
                DeliveryStop(
                    session=child,
                    name=stop.name,
                    raw_address=stop.raw_address,
                    product_code=stop.product_code,
                    recipient_name=stop.recipient_name,
                    recipient_phone=stop.recipient_phone,
                    lat=stop.lat,
                    lng=stop.lng,
                    geocode_status=stop.geocode_status,
                    geocode_error=stop.geocode_error,
                )
            )
        DeliveryStop.objects.bulk_create(child_stops)

        sub_routes.append(
            {
                "id": str(child.id),
                "name": child.name,
                "stop_count": len(cluster),
                "owner_id": owner.id if owner else None,
                "owner_name": owner.username if owner else None,
            }
        )

    session.status = DeliverySession.Status.SPLIT
    session.save(update_fields=["status"])

    stop_counts = [len(c) for c in clusters]
    return Response(
        {
            "parent_id": str(session.id),
            "sub_routes": sub_routes,
            "cluster_summary": {
                "total_stops": len(geocoded_stops),
                "skipped_stops": skipped_count,
                "n_routes": len(clusters),
                "avg_stops_per_route": round(len(geocoded_stops) / len(clusters), 1),
                "min_stops": min(stop_counts),
                "max_stops": max(stop_counts),
            },
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@transaction.atomic
def move_stop(request, session_id):
    """Move a stop from one sub-route to a sibling sub-route."""
    if not require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        source_session = DeliverySession.objects.select_for_update().get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    stop_id = request.data.get("stop_id")
    to_session_id = request.data.get("to_session_id")

    if not stop_id or not to_session_id:
        return Response(
            {"error": "stop_id and to_session_id are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        stop = source_session.stops.get(id=int(stop_id))
    except (DeliveryStop.DoesNotExist, ValueError, TypeError):
        return Response({"error": "Stop not found in this session."}, status=status.HTTP_404_NOT_FOUND)

    try:
        target_session = DeliverySession.objects.select_for_update().get(id=to_session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Target session not found."}, status=status.HTTP_404_NOT_FOUND)

    if source_session.parent_id is None or source_session.parent_id != target_session.parent_id:
        return Response(
            {"error": "Can only move stops between sibling sub-routes (same parent)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if source_session.status == DeliverySession.Status.IN_PROGRESS:
        return Response(
            {"error": "Cannot move stops from an in-progress route."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if target_session.status == DeliverySession.Status.IN_PROGRESS:
        return Response(
            {"error": "Cannot move stops to an in-progress route."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    stop.session = target_session
    stop.sequence_order = None
    stop.save(update_fields=["session_id", "sequence_order"])

    for s in [source_session, target_session]:
        s.route_geometry = None
        s.route_segments = None
        s.total_duration = None
        s.total_distance = None
        s.save(update_fields=["route_geometry", "route_segments", "total_duration", "total_distance"])

    return Response(
        {
            "stop_id": stop.id,
            "from_session_id": str(source_session.id),
            "to_session_id": str(target_session.id),
            "from_count": source_session.stops.count(),
            "to_count": target_session.stops.count(),
        }
    )


@api_view(["DELETE"])
@transaction.atomic
def uncluster_session(request, session_id):
    """Undo a split: delete all sub-routes and reset parent to not_started."""
    if not require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        session = DeliverySession.objects.select_for_update().get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    if session.status != DeliverySession.Status.SPLIT:
        return Response(
            {"error": "Session is not split."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if session.sub_routes.filter(status=DeliverySession.Status.IN_PROGRESS).exists():
        return Response(
            {"error": "Cannot undo split while a sub-route is in progress."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    deleted_count = session.sub_routes.count()
    session.sub_routes.all().delete()
    session.status = DeliverySession.Status.NOT_STARTED
    session.save(update_fields=["status"])

    return Response({"parent_id": str(session.id), "deleted_routes": deleted_count})


@api_view(["GET"])
def session_districts(request, session_id):
    """City districts present in a session's geocoded stops, for the split planner."""
    if not require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        session = DeliverySession.objects.get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    stops = session.stops.filter(geocode_status__in=["success", "skipped"], lat__isnull=False, lng__isnull=False).only(
        "raw_address"
    )

    counts = {}
    unknown = 0
    total = 0
    for stop in stops:
        total += 1
        district = extract_district(stop.raw_address)
        if district is None:
            unknown += 1
        else:
            counts[district] = counts.get(district, 0) + 1

    return Response(
        {
            "districts": [
                {"district": d, "label": district_label(d), "stop_count": c} for d, c in sorted(counts.items())
            ],
            "unknown_district_stops": unknown,
            "total_stops": total,
        }
    )


@api_view(["DELETE"])
@transaction.atomic
def remove_stop(request, session_id, stop_id):
    """Remove a single stop from a route during split review."""
    if not require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        session = DeliverySession.objects.select_for_update().get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    if session.status == DeliverySession.Status.IN_PROGRESS:
        return Response(
            {"error": "Cannot remove stops from an in-progress route."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        stop = session.stops.get(id=stop_id)
    except DeliveryStop.DoesNotExist:
        return Response({"error": "Stop not found in this session."}, status=status.HTTP_404_NOT_FOUND)

    stop.delete()

    session.route_geometry = None
    session.route_segments = None
    session.total_duration = None
    session.total_distance = None
    session.save(update_fields=["route_geometry", "route_segments", "total_duration", "total_distance"])

    return Response({"removed_stop_id": stop_id, "remaining_stops": session.stops.count()})
