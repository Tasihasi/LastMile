from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..clustering import calculate_n_clusters, cluster_stops
from ..models import DeliverySession, DeliveryStop
from .helpers import require_planner


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

    max_stops = int(request.data.get("max_stops_per_route", 48))
    n_routes_param = request.data.get("n_routes")
    n_routes = (
        int(n_routes_param) if n_routes_param is not None else calculate_n_clusters(len(geocoded_stops), max_stops)
    )

    clusters = cluster_stops(geocoded_stops, n_routes, max_stops_per_cluster=max_stops)

    sub_routes = []
    for i, cluster in enumerate(clusters, start=1):
        child = DeliverySession.objects.create(
            parent=session,
            owner=None,
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
