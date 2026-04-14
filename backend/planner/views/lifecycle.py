from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import DeliverySession, DeliveryStop
from ..serializers import DeliveryStopSerializer, SessionListSerializer
from .helpers import get_user_session


@api_view(["PATCH"])
def start_route(request, session_id):
    """Biker starts a route — sets status to in_progress."""
    session = get_user_session(request, session_id)
    if not session:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    if session.status == DeliverySession.Status.SPLIT:
        return Response(
            {"error": "Cannot start a split session. Start the sub-routes instead."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if session.status != "not_started":
        return Response({"error": "Route already started."}, status=status.HTTP_400_BAD_REQUEST)

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
    session = get_user_session(request, session_id)
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

    next_stop = (
        session.stops.filter(sequence_order__isnull=False, delivery_status="pending").order_by("sequence_order").first()
    )

    if next_stop:
        session.current_stop_index = next_stop.sequence_order
        session.save(update_fields=["current_stop_index"])
    else:
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
