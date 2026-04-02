import uuid

from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    class Role(models.TextChoices):
        BIKER = "biker", "Biker"
        PLANNER = "planner", "Planner"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.BIKER)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class DeliverySession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessions", null=True, blank=True
    )
    original_file = models.FileField(upload_to="uploads/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.id} ({self.created_at:%Y-%m-%d %H:%M})"


class DeliveryStop(models.Model):
    class GeocodeStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    session = models.ForeignKey(DeliverySession, on_delete=models.CASCADE, related_name="stops")
    name = models.CharField(max_length=255)
    raw_address = models.CharField(max_length=500, blank=True, default="")
    product_code = models.CharField(max_length=100, blank=True, default="")
    recipient_name = models.CharField(max_length=255, blank=True, default="")
    recipient_phone = models.CharField(max_length=50, blank=True, default="")
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    geocode_status = models.CharField(
        max_length=20,
        choices=GeocodeStatus.choices,
        default=GeocodeStatus.PENDING,
    )
    geocode_error = models.CharField(max_length=500, blank=True, default="")
    sequence_order = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.name} ({self.geocode_status})"


class SharedRoute(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(DeliverySession, on_delete=models.CASCADE, related_name="shares")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Share {self.id} -> Session {self.session_id}"
