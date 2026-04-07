from django.contrib.auth.models import User
from rest_framework import serializers

from .models import DeliverySession, DeliveryStop, SharedRoute, UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = UserProfile
        fields = ["user_id", "username", "role"]


class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="profile.role", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "role"]


class DeliveryStopSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryStop
        fields = [
            "id",
            "name",
            "raw_address",
            "product_code",
            "recipient_name",
            "recipient_phone",
            "lat",
            "lng",
            "geocode_status",
            "geocode_error",
            "sequence_order",
            "delivery_status",
        ]


class DeliverySessionSerializer(serializers.ModelSerializer):
    stops = DeliveryStopSerializer(many=True, read_only=True)
    needs_geocoding = serializers.SerializerMethodField()
    owner_name = serializers.CharField(source="owner.username", read_only=True, default=None)
    parent_id = serializers.UUIDField(read_only=True, default=None)
    sub_route_count = serializers.IntegerField(source="sub_routes.count", read_only=True)

    class Meta:
        model = DeliverySession
        fields = [
            "id",
            "name",
            "created_at",
            "owner_name",
            "parent_id",
            "sub_route_count",
            "stops",
            "needs_geocoding",
            "total_duration",
            "total_distance",
            "status",
            "started_at",
            "finished_at",
            "current_stop_index",
            "route_geometry",
            "route_segments",
        ]

    def get_needs_geocoding(self, obj):
        return obj.stops.filter(geocode_status="pending").exists()


class SessionListSerializer(serializers.ModelSerializer):
    """Lighter serializer for session lists (no stops).

    Supports pre-annotated querysets (_stop_count, _delivered_count, etc.)
    for efficient list views, with fallback queries for single-object usage.
    """

    stop_count = serializers.SerializerMethodField()
    owner_name = serializers.CharField(source="owner.username", read_only=True, default=None)
    parent_id = serializers.UUIDField(read_only=True, default=None)
    sub_route_count = serializers.SerializerMethodField()
    delivered_count = serializers.SerializerMethodField()
    not_received_count = serializers.SerializerMethodField()
    current_stop_name = serializers.SerializerMethodField()

    class Meta:
        model = DeliverySession
        fields = [
            "id",
            "name",
            "created_at",
            "owner_name",
            "parent_id",
            "sub_route_count",
            "stop_count",
            "total_duration",
            "total_distance",
            "status",
            "started_at",
            "finished_at",
            "current_stop_index",
            "delivered_count",
            "not_received_count",
            "current_stop_name",
        ]

    def get_stop_count(self, obj):
        if hasattr(obj, "_stop_count"):
            return obj._stop_count
        return obj.stops.count()

    def get_sub_route_count(self, obj):
        if hasattr(obj, "_sub_route_count"):
            return obj._sub_route_count
        return obj.sub_routes.count()

    def get_delivered_count(self, obj):
        if hasattr(obj, "_delivered_count"):
            return obj._delivered_count
        return obj.stops.filter(delivery_status="delivered").count()

    def get_not_received_count(self, obj):
        if hasattr(obj, "_not_received_count"):
            return obj._not_received_count
        return obj.stops.filter(delivery_status="not_received").count()

    def get_current_stop_name(self, obj):
        if hasattr(obj, "_current_stop_name"):
            return obj._current_stop_name
        if obj.current_stop_index is None:
            return None
        stop = obj.stops.filter(sequence_order=obj.current_stop_index).first()
        return stop.name if stop else None


class ActiveSessionStopSerializer(serializers.ModelSerializer):
    """Minimal stop data for aggregate map — just coords, name, sequence, status."""

    class Meta:
        model = DeliveryStop
        fields = ["id", "name", "lat", "lng", "sequence_order", "delivery_status"]


class ActiveSessionSerializer(serializers.ModelSerializer):
    """Session data for the planner aggregate map.

    Uses prefetched stops to compute counts in Python, avoiding N+1 queries.
    """

    stops = ActiveSessionStopSerializer(many=True, read_only=True)
    owner_name = serializers.CharField(source="owner.username", read_only=True, default=None)
    owner_id = serializers.IntegerField(source="owner.id", read_only=True, default=None)
    delivered_count = serializers.SerializerMethodField()
    stop_count = serializers.SerializerMethodField()
    current_stop_name = serializers.SerializerMethodField()

    class Meta:
        model = DeliverySession
        fields = [
            "id",
            "name",
            "owner_name",
            "owner_id",
            "status",
            "started_at",
            "current_stop_index",
            "stop_count",
            "delivered_count",
            "current_stop_name",
            "total_duration",
            "total_distance",
            "route_geometry",
            "stops",
        ]

    def _get_cached_stops(self, obj):
        """Get stops from prefetch cache to avoid extra queries."""
        return list(obj.stops.all())

    def get_stop_count(self, obj):
        return len(self._get_cached_stops(obj))

    def get_delivered_count(self, obj):
        done_statuses = {"delivered", "not_received", "skipped"}
        return sum(1 for s in self._get_cached_stops(obj) if s.delivery_status in done_statuses)

    def get_current_stop_name(self, obj):
        if obj.current_stop_index is None:
            return None
        for s in self._get_cached_stops(obj):
            if s.sequence_order == obj.current_stop_index:
                return s.name
        return None


class SharedRouteSerializer(serializers.ModelSerializer):
    session = DeliverySessionSerializer(read_only=True)

    class Meta:
        model = SharedRoute
        fields = ["id", "session", "created_at"]
