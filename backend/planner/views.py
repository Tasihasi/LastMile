import contextlib
import json

from django.contrib.auth.models import User
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .geocoder import geocode_address
from .models import DeliverySession, DeliveryStop, SharedRoute, UserProfile
from .optimizer import get_route_details, optimize_route
from .parsers import parse_file
from .serializers import (
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
def list_sessions(request):
    """List sessions. Bikers see their own; planners see all (optionally filtered by owner_id)."""
    if hasattr(request.user, "profile") and request.user.profile.role == "planner":
        qs = DeliverySession.objects.all()
        owner_id = request.query_params.get("owner_id")
        if owner_id:
            qs = qs.filter(owner_id=owner_id)
    else:
        qs = DeliverySession.objects.filter(owner=request.user)

    qs = qs.order_by("-created_at")
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

    # Determine owner: planners can assign to a biker via owner_id
    owner = request.user
    owner_id = request.data.get("owner_id")
    if owner_id and hasattr(request.user, "profile") and request.user.profile.role == "planner":
        with contextlib.suppress(User.DoesNotExist, ValueError, TypeError):
            owner = User.objects.get(id=int(owner_id))

    session = DeliverySession.objects.create(original_file=file, owner=owner)

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

    # Optional depot/home location
    depot = None
    depot_lat = request.data.get("depot_lat")
    depot_lng = request.data.get("depot_lng")
    if depot_lat is not None and depot_lng is not None:
        with contextlib.suppress(ValueError, TypeError):
            depot = (float(depot_lat), float(depot_lng))

    try:
        ordered_ids = optimize_route(located_stops, depot=depot)
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
