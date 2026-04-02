import uuid

from django.db import models


class DeliverySession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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

    session = models.ForeignKey(
        DeliverySession, on_delete=models.CASCADE, related_name="stops"
    )
    name = models.CharField(max_length=255)
    raw_address = models.CharField(max_length=500, blank=True, default="")
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
