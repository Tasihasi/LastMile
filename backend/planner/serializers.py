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
        ]


class DeliverySessionSerializer(serializers.ModelSerializer):
    stops = DeliveryStopSerializer(many=True, read_only=True)
    needs_geocoding = serializers.SerializerMethodField()
    owner_name = serializers.CharField(source="owner.username", read_only=True, default=None)

    class Meta:
        model = DeliverySession
        fields = ["id", "created_at", "owner_name", "stops", "needs_geocoding"]

    def get_needs_geocoding(self, obj):
        return obj.stops.filter(geocode_status="pending").exists()


class SessionListSerializer(serializers.ModelSerializer):
    """Lighter serializer for session lists (no stops)."""

    stop_count = serializers.IntegerField(source="stops.count", read_only=True)
    owner_name = serializers.CharField(source="owner.username", read_only=True, default=None)

    class Meta:
        model = DeliverySession
        fields = ["id", "created_at", "owner_name", "stop_count"]


class SharedRouteSerializer(serializers.ModelSerializer):
    session = DeliverySessionSerializer(read_only=True)

    class Meta:
        model = SharedRoute
        fields = ["id", "session", "created_at"]
