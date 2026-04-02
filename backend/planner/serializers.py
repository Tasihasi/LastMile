from rest_framework import serializers

from .models import DeliverySession, DeliveryStop


class DeliveryStopSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryStop
        fields = [
            "id",
            "name",
            "raw_address",
            "lat",
            "lng",
            "geocode_status",
            "geocode_error",
            "sequence_order",
        ]


class DeliverySessionSerializer(serializers.ModelSerializer):
    stops = DeliveryStopSerializer(many=True, read_only=True)
    needs_geocoding = serializers.SerializerMethodField()

    class Meta:
        model = DeliverySession
        fields = ["id", "created_at", "stops", "needs_geocoding"]

    def get_needs_geocoding(self, obj):
        return obj.stops.filter(geocode_status="pending").exists()
