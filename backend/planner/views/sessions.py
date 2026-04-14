import contextlib
import json

import requests
from django.conf import settings as django_settings
from django.contrib.auth.models import User
from django.db.models import Count, OuterRef, Q, Subquery
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..geocoder import geocode_address
from ..models import DeliverySession, DeliveryStop, SharedRoute
from ..optimizer import get_route_details, optimize_route
from ..parsers import parse_file
from ..serializers import (
    ActiveSessionSerializer,
    DeliverySessionSerializer,
    DeliveryStopSerializer,
    SessionListSerializer,
    SharedRouteSerializer,
    UserSerializer,
)
from .helpers import get_user_session, require_planner


@api_view(["GET"])
def list_bikers(request):
    if not require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    bikers = User.objects.filter(profile__role="biker").select_related("profile")
    return Response(UserSerializer(bikers, many=True).data)


@api_view(["GET"])
def active_sessions(request):
    """All in-progress sessions with stops and route geometry for aggregate map."""
    if not require_planner(request):
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
        qs = DeliverySession.objects.exclude(status=DeliverySession.Status.SPLIT)
        owner_id = request.query_params.get("owner_id")
        if owner_id:
            qs = qs.filter(owner_id=owner_id)
    else:
        qs = DeliverySession.objects.filter(owner=request.user).exclude(status=DeliverySession.Status.SPLIT)

    qs = _annotate_session_list(qs).order_by("-created_at")
    return Response(SessionListSerializer(qs, many=True).data)


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

    is_planner = hasattr(request.user, "profile") and request.user.profile.role == "planner"
    owner = None if is_planner else request.user
    owner_id = request.data.get("owner_id")
    if owner_id and is_planner:
        with contextlib.suppress(User.DoesNotExist, ValueError, TypeError):
            owner = User.objects.get(id=int(owner_id))

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
    session = get_user_session(request, session_id)
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
    session = get_user_session(request, session_id)
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
    session = get_user_session(request, session_id)
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
    session = get_user_session(request, session_id)
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

    id_to_stop = {s.id: s for s in located_stops}
    for order, stop_id in enumerate(ordered_ids, start=1):
        stop = id_to_stop[stop_id]
        stop.sequence_order = order
        stop.save(update_fields=["sequence_order"])

    ordered_stops = [id_to_stop[sid] for sid in ordered_ids]
    try:
        route = get_route_details(ordered_stops, depot=depot)
    except Exception:
        route = None

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


@api_view(["POST"])
def share_session(request, session_id):
    session = get_user_session(request, session_id)
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


@api_view(["DELETE"])
def delete_session(request, session_id):
    if not require_planner(request):
        return Response({"error": "Planner access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        session = DeliverySession.objects.get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    session.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["PATCH"])
def assign_session(request, session_id):
    if not require_planner(request):
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
    if not require_planner(request):
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
