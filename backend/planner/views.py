import json

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from .geocoder import geocode_address
from .models import DeliverySession, DeliveryStop
from .optimizer import get_route_geometry, optimize_route
from .parsers import parse_file
from .serializers import DeliverySessionSerializer, DeliveryStopSerializer


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

    session = DeliverySession.objects.create(original_file=file)

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
    try:
        session = DeliverySession.objects.get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response(
            {"error": "Session not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

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
    try:
        session = DeliverySession.objects.get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response(
            {"error": "Session not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

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
    try:
        session = DeliverySession.objects.get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response(
            {"error": "Session not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

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
    try:
        session = DeliverySession.objects.get(id=session_id)
    except DeliverySession.DoesNotExist:
        return Response(
            {"error": "Session not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    located_stops = list(session.stops.filter(lat__isnull=False, lng__isnull=False))

    if len(located_stops) < 2:
        return Response(
            {"error": "Need at least 2 geocoded stops to optimize."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        ordered_ids = optimize_route(located_stops)
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

    # Get the route geometry along real roads
    ordered_stops = [id_to_stop[sid] for sid in ordered_ids]
    try:
        geometry = get_route_geometry(ordered_stops)
    except Exception:
        geometry = None

    return Response(
        {
            "optimized_stops": DeliveryStopSerializer(ordered_stops, many=True).data,
            "route_geometry": geometry,
        }
    )
