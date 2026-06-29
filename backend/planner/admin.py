from django.contrib import admin

from .models import DeliverySession, DeliveryStop, SharedRoute, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email")
    autocomplete_fields = ("user",)


class DeliveryStopInline(admin.TabularInline):
    model = DeliveryStop
    extra = 0
    fields = (
        "name",
        "raw_address",
        "sequence_order",
        "geocode_status",
        "delivery_status",
    )
    readonly_fields = ("geocode_status",)
    show_change_link = True


@admin.register(DeliverySession)
class DeliverySessionAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "status", "parent", "created_at", "stop_count")
    list_filter = ("status", "created_at")
    search_fields = ("name", "owner__username", "id")
    date_hierarchy = "created_at"
    autocomplete_fields = ("owner", "parent")
    readonly_fields = ("id", "created_at", "started_at", "finished_at")
    inlines = [DeliveryStopInline]
    list_select_related = ("owner", "parent")

    @admin.display(description="Stops", ordering="stops__count")
    def stop_count(self, obj):
        return obj.stops.count()


@admin.register(DeliveryStop)
class DeliveryStopAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "session",
        "sequence_order",
        "geocode_status",
        "delivery_status",
    )
    list_filter = ("geocode_status", "delivery_status")
    search_fields = ("name", "raw_address", "recipient_name", "product_code")
    autocomplete_fields = ("session",)
    list_select_related = ("session",)


@admin.register(SharedRoute)
class SharedRouteAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "created_at")
    search_fields = ("id", "session__id", "session__name")
    date_hierarchy = "created_at"
    autocomplete_fields = ("session",)
    readonly_fields = ("id", "created_at")
