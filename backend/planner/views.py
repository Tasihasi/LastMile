import contextlib
import json

import requests
from django.conf import settings as django_settings
from django.contrib.auth.models import User
from django.db.models import Count, OuterRef, Q, Subquery
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .clustering import calculate_n_clusters, cluster_stops
from .geocoder import geocode_address
from .models import DeliverySession, DeliveryStop, SharedRoute, UserProfile
from .optimizer import get_route_details, optimize_route
from .parsers import parse_file
from .serializers import (
    ActiveSessionSerializer,
    DeliverySessionSerializer,
    DeliveryStopSerializer,
    SessionListSerializer,
    SharedRouteSerializer,
    UserSerializer,
)

# ============================================
# Helpers
# ============================================


def _get_user_session(request, session_id):
    """Get a session, enforcing ownership for bikers."""
    try:
        session = DeliverySession.objects.get(id=session_id)
    except DeliverySession.DoesNotExist:
        return None

    # Planners can access any session; bikers only their own
    if hasattr(request.user, "profile") and request.user.profile.role == "planner":
        return session
    if session.owner == request.user:
        return session
    # Unowned sessions (legacy) are accessible to anyone
    if session.owner is None:
        return session
    return None


# ============================================
# Auth Endpoints
# ============================================


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get("username", "").strip()
    role = request.data.get("role", "biker").strip()

    if not username:
        return Response({"error": "Username is required."}, status=status.HTTP_400_BAD_REQUEST)
    if role not in ("biker", "planner"):
        return Response({"error": "Role must be 'biker' or 'planner'."}, status=status.HTTP_400_BAD_REQUEST)

    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_unusable_password()
        user.save()

    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"role": role})
    if not created and profile.role != role:
        # Update role if user logs in with different role
        profile.role = role
        profile.save()

    token, _ = Token.objects.get_or_create(user=user)

    return Response(
        {
            "token": token.key,
            "user": UserSerializer(user).data,
        }
    )


@api_view(["GET"])
def me_view(request):
    return Response(UserSerializer(request.user).data)


@api_view(["POST"])
def logout_view(request):
    Token.objects.filter(user=request.user).delete()
    return Response({"message": "Logged out."})


# ============================================
# Planner Endpoints
# ============================================


@api_view(["GET"])
def list_bikers(request):
    if not hasattr(request.user, "profile") or request.user.profile.role != "planner":
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    bikers = User.objects.filter(profile__role="biker").select_related("profile")
    return Response(UserSerializer(bikers, many=True).data)


@api_view(["GET"])
def active_sessions(request):
    """All in-progress sessions with stops and route geometry for aggregate map."""
    if not _require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    qs = DeliverySession.objects.filter(status="in_progress").select_related("owner").prefetch_related("stops")
    return Response(ActiveSessionSerializer(qs, many=True).data)


def _annotate_session_list(qs):
    """Add computed annotations to a session queryset to avoid N+1 queries."""
    return qs.select_related("owner").annotate(
        _stop_count=Count("stops", distinct=True),
        _sub_route_count=Count("sub_routes", distinct=True),
        _delivered_count=Count("stops", filter=Q(stops__delivery_status="delivered"), distinct=True),
        _not_received_count=Count("stops", filter=Q(stops__delivery_status="not_received"), distinct=True),
        _current_stop_name=Subquery(
            DeliveryStop.objects.filter(
                session=OuterRef("pk"),
                sequence_order=OuterRef("current_stop_index"),
            ).values("name")[:1]
        ),
    )


@api_view(["GET"])
def list_sessions(request):
    """List sessions. Bikers see their own; planners see all (optionally filtered by owner_id)."""
    if hasattr(request.user, "profile") and request.user.profile.role == "planner":
        qs = DeliverySession.objects.all()
        owner_id = request.query_params.get("owner_id")
        if owner_id:
            qs = qs.filter(owner_id=owner_id)
    else:
        # Bikers see only their own sessions, excluding split parents (which have no deliverable stops)
        qs = DeliverySession.objects.filter(owner=request.user).exclude(status=DeliverySession.Status.SPLIT)

    qs = _annotate_session_list(qs).order_by("-created_at")
    return Response(SessionListSerializer(qs, many=True).data)


# ============================================
# Session Endpoints (existing, now with auth)
# ============================================


@api_view(["POST"])
@parser_classes([MultiPartParser])
def upload_file(request):
    file = request.FILES.get("file")
    if not file:
        return Response(
            {"error": "No file provided."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        rows = parse_file(file, file.name)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        return Response(
            {"error": "Failed to parse file. Check the format and try again."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not rows:
        return Response(
            {"error": "No valid stops found in file. Each row needs a name and either an address or lat/lng."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Determine owner: planners upload as unassigned unless they specify a biker
    is_planner = hasattr(request.user, "profile") and request.user.profile.role == "planner"
    owner = None if is_planner else request.user
    owner_id = request.data.get("owner_id")
    if owner_id and is_planner:
        with contextlib.suppress(User.DoesNotExist, ValueError, TypeError):
            owner = User.objects.get(id=int(owner_id))

    # Auto-generate route name from filename
    raw_name = file.name.rsplit(".", 1)[0] if "." in file.name else file.name
    route_name = raw_name.replace("_", " ").replace("-", " ").strip().title()

    session = DeliverySession.objects.create(original_file=file, owner=owner, name=route_name)

    stops = []
    for row in rows:
        has_coords = row["lat"] is not None and row["lng"] is not None
        stop = DeliveryStop(
            session=session,
            name=row["name"],
            raw_address=row.get("address", ""),
            product_code=row.get("product_code", ""),
            recipient_name=row.get("recipient_name", ""),
            recipient_phone=row.get("recipient_phone", ""),
            lat=row["lat"],
            lng=row["lng"],
            geocode_status="skipped" if has_coords else "pending",
        )
        stops.append(stop)

    DeliveryStop.objects.bulk_create(stops)

    session.refresh_from_db()
    serializer = DeliverySessionSerializer(session)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def get_session(request, session_id):
    session = _get_user_session(request, session_id)
    if not session:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    serializer = DeliverySessionSerializer(session)
    return Response(serializer.data)


def _geocode_stream(session_id):
    """Generator that geocodes pending stops and yields NDJSON lines."""
    try:
        session = DeliverySession.objects.get(id=session_id)
    except DeliverySession.DoesNotExist:
        yield json.dumps({"error": "Session not found."}) + "\n"
        return

    pending_stops = session.stops.filter(geocode_status="pending")
    total = pending_stops.count()

    for i, stop in enumerate(pending_stops):
        result = geocode_address(stop.raw_address)

        if result:
            stop.lat, stop.lng = result
            stop.geocode_status = "success"
        else:
            stop.geocode_status = "failed"
            stop.geocode_error = "Address not found"

        stop.save()

        yield (
            json.dumps(
                {
                    "stop": DeliveryStopSerializer(stop).data,
                    "progress": {"current": i + 1, "total": total},
                }
            )
            + "\n"
        )


@api_view(["POST"])
def geocode_stops(request, session_id):
    session = _get_user_session(request, session_id)
    if not session:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    pending = session.stops.filter(geocode_status="pending").count()
    if pending == 0:
        return Response({"message": "No stops to geocode."})

    response = StreamingHttpResponse(
        _geocode_stream(session_id),
        content_type="application/x-ndjson",
    )
    return response


@api_view(["GET"])
def geocode_status(request, session_id):
    session = _get_user_session(request, session_id)
    if not session:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    stops = session.stops.all()
    total = stops.count()
    pending = stops.filter(geocode_status="pending").count()
    success = stops.filter(geocode_status="success").count()
    failed = stops.filter(geocode_status="failed").count()

    return Response(
        {
            "total": total,
            "pending": pending,
            "success": success,
            "failed": failed,
            "stops": DeliveryStopSerializer(stops, many=True).data,
        }
    )


@api_view(["POST"])
def optimize(request, session_id):
    session = _get_user_session(request, session_id)
    if not session:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    located_stops = list(session.stops.filter(lat__isnull=False, lng__isnull=False))

    if len(located_stops) < 2:
        return Response(
            {"error": "Need at least 2 geocoded stops to optimize."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not django_settings.ORS_API_KEY and not django_settings.E2E_MOCK:
        return Response(
            {
                "error": "Route optimization is not available: ORS_API_KEY is not configured. "
                "Get a free key at https://openrouteservice.org and add it to your .env file."
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # Optional depot/home location
    depot = None
    depot_lat = request.data.get("depot_lat")
    depot_lng = request.data.get("depot_lng")
    if depot_lat is not None and depot_lng is not None:
        with contextlib.suppress(ValueError, TypeError):
            depot = (float(depot_lat), float(depot_lng))

    try:
        ordered_ids = optimize_route(located_stops, depot=depot)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 403):
            return Response(
                {
                    "error": "Route optimization failed: ORS_API_KEY is invalid or expired. "
                    "Check your key at https://openrouteservice.org."
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(
            {"error": f"Route optimization failed: {e}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except Exception as e:
        return Response(
            {"error": f"Route optimization failed: {e}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # Update sequence_order on each stop
    id_to_stop = {s.id: s for s in located_stops}
    for order, stop_id in enumerate(ordered_ids, start=1):
        stop = id_to_stop[stop_id]
        stop.sequence_order = order
        stop.save(update_fields=["sequence_order"])

    # Get the route geometry and timing along real roads
    ordered_stops = [id_to_stop[sid] for sid in ordered_ids]
    try:
        route = get_route_details(ordered_stops, depot=depot)
    except Exception:
        route = None

    # Persist totals, geometry, and segments on session
    if route:
        session.total_duration = route["total_duration"]
        session.total_distance = route["total_distance"]
        session.route_geometry = route["geometry"]
        session.route_segments = route["segments"]
        session.save(update_fields=["total_duration", "total_distance", "route_geometry", "route_segments"])

    return Response(
        {
            "optimized_stops": DeliveryStopSerializer(ordered_stops, many=True).data,
            "route_geometry": route["geometry"] if route else None,
            "route_segments": route["segments"] if route else None,
            "total_duration": route["total_duration"] if route else None,
            "total_distance": route["total_distance"] if route else None,
        }
    )


# ============================================
# Share Endpoints
# ============================================


@api_view(["POST"])
def share_session(request, session_id):
    session = _get_user_session(request, session_id)
    if not session:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    share = SharedRoute.objects.create(session=session)
    return Response({"share_id": str(share.id)}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_shared_route(request, share_id):
    try:
        share = SharedRoute.objects.select_related("session").get(id=share_id)
    except SharedRoute.DoesNotExist:
        return Response({"error": "Shared route not found."}, status=status.HTTP_404_NOT_FOUND)

    return Response(SharedRouteSerializer(share).data)


# ============================================
# Session Management (planner only)
# ============================================


def _require_planner(request):
    return hasattr(request.user, "profile") and request.user.profile.role == "planner"


@api_view(["DELETE"])
def delete_session(request, session_id):
    if not _require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        session = DeliverySession.objects.get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    session.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["PATCH"])
def assign_session(request, session_id):
    if not _require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        session = DeliverySession.objects.get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    owner_id = request.data.get("owner_id")

    if owner_id is None:
        session.owner = None
        session.save(update_fields=["owner"])
        return Response({"message": "Session unassigned.", "owner_name": None})

    try:
        new_owner = User.objects.get(id=int(owner_id))
    except (User.DoesNotExist, ValueError, TypeError):
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    session.owner = new_owner
    session.save(update_fields=["owner"])
    return Response({"message": "Session reassigned.", "owner_name": new_owner.username})


@api_view(["PATCH"])
def rename_session(request, session_id):
    if not _require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        session = DeliverySession.objects.get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    name = request.data.get("name", "").strip()
    if not name:
        return Response({"error": "Name is required."}, status=status.HTTP_400_BAD_REQUEST)

    session.name = name
    session.save(update_fields=["name"])
    return Response({"name": session.name})


# ============================================
# Clustering (planner)
# ============================================


@api_view(["POST"])
def cluster_session(request, session_id):
    """Split a large session into clustered sub-routes using KMeans."""
    if not _require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        session = DeliverySession.objects.get(id=session_id)
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

    # Get stops with valid coordinates (geocoded or uploaded with coords)
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

    # Run KMeans clustering
    clusters = cluster_stops(geocoded_stops, n_routes, max_stops_per_cluster=max_stops)

    # Create child sessions with copied stops
    sub_routes = []
    for i, cluster in enumerate(clusters, start=1):
        child = DeliverySession.objects.create(
            parent=session,
            owner=None,
            name=f"Route {i} of {len(clusters)}",
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

    # Mark parent as split
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
def move_stop(request, session_id):
    """Move a stop from one sub-route to a sibling sub-route."""
    if not _require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        source_session = DeliverySession.objects.get(id=session_id)
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
        target_session = DeliverySession.objects.get(id=to_session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Target session not found."}, status=status.HTTP_404_NOT_FOUND)

    # Validate both sessions share the same parent
    if source_session.parent_id is None or source_session.parent_id != target_session.parent_id:
        return Response(
            {"error": "Can only move stops between sibling sub-routes (same parent)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Block moves if either session is in progress
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

    # Move the stop
    stop.session = target_session
    stop.sequence_order = None  # Needs re-optimization
    stop.save(update_fields=["session_id", "sequence_order"])

    # Clear optimization data on both sessions since routes changed
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
def uncluster_session(request, session_id):
    """Undo a split: delete all sub-routes and reset parent to not_started."""
    if not _require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        session = DeliverySession.objects.get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    if session.status != DeliverySession.Status.SPLIT:
        return Response(
            {"error": "Session is not split."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Block if any sub-route is in progress
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


# ============================================
# Route Lifecycle (biker)
# ============================================


@api_view(["PATCH"])
def start_route(request, session_id):
    """Biker starts a route — sets status to in_progress."""
    session = _get_user_session(request, session_id)
    if not session:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    if session.status == DeliverySession.Status.SPLIT:
        return Response(
            {"error": "Cannot start a split session. Start the sub-routes instead."}, status=status.HTTP_400_BAD_REQUEST
        )

    if session.status != "not_started":
        return Response({"error": "Route already started."}, status=status.HTTP_400_BAD_REQUEST)

    # Find the first stop in optimized order
    first_stop = session.stops.filter(sequence_order__isnull=False).order_by("sequence_order").first()
    if not first_stop:
        return Response({"error": "Route must be optimized before starting."}, status=status.HTTP_400_BAD_REQUEST)

    session.status = "in_progress"
    session.started_at = timezone.now()
    session.current_stop_index = first_stop.sequence_order
    session.save(update_fields=["status", "started_at", "current_stop_index"])

    return Response(SessionListSerializer(session).data)


@api_view(["PATCH"])
def update_stop_status(request, session_id, stop_id):
    """Biker marks a stop as delivered/not_received/skipped."""
    session = _get_user_session(request, session_id)
    if not session:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get("status")
    if new_status not in ("delivered", "not_received", "skipped"):
        return Response(
            {"error": "Status must be 'delivered', 'not_received', or 'skipped'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        stop = session.stops.get(id=stop_id)
    except DeliveryStop.DoesNotExist:
        return Response({"error": "Stop not found."}, status=status.HTTP_404_NOT_FOUND)

    stop.delivery_status = new_status
    stop.save(update_fields=["delivery_status"])

    # Auto-advance current_stop_index to next pending stop
    next_stop = (
        session.stops.filter(sequence_order__isnull=False, delivery_status="pending").order_by("sequence_order").first()
    )

    if next_stop:
        session.current_stop_index = next_stop.sequence_order
        session.save(update_fields=["current_stop_index"])
    else:
        # All stops done — finish the route
        session.status = "finished"
        session.finished_at = timezone.now()
        session.current_stop_index = None
        session.save(update_fields=["status", "finished_at", "current_stop_index"])

    return Response(
        {
            "stop": DeliveryStopSerializer(stop).data,
            "session_status": session.status,
            "current_stop_index": session.current_stop_index,
        }
    )
