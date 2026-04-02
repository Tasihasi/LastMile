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

    class Meta:
        model = DeliverySession
        fields = [
            "id",
            "name",
            "created_at",
            "owner_name",
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
    """Lighter serializer for session lists (no stops)."""

    stop_count = serializers.IntegerField(source="stops.count", read_only=True)
    owner_name = serializers.CharField(source="owner.username", read_only=True, default=None)
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

    def get_delivered_count(self, obj):
        return obj.stops.filter(delivery_status="delivered").count()

    def get_not_received_count(self, obj):
        return obj.stops.filter(delivery_status="not_received").count()

    def get_current_stop_name(self, obj):
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
    """Session data for the planner aggregate map."""

    stops = ActiveSessionStopSerializer(many=True, read_only=True)
    owner_name = serializers.CharField(source="owner.username", read_only=True, default=None)
    owner_id = serializers.IntegerField(source="owner.id", read_only=True, default=None)
    delivered_count = serializers.SerializerMethodField()
    stop_count = serializers.IntegerField(source="stops.count", read_only=True)
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

    def get_delivered_count(self, obj):
        return obj.stops.filter(delivery_status__in=["delivered", "not_received", "skipped"]).count()

    def get_current_stop_name(self, obj):
        if obj.current_stop_index is None:
            return None
        stop = obj.stops.filter(sequence_order=obj.current_stop_index).first()
        return stop.name if stop else None


class SharedRouteSerializer(serializers.ModelSerializer):
    session = DeliverySessionSerializer(read_only=True)

    class Meta:
        model = SharedRoute
        fields = ["id", "session", "created_at"]
