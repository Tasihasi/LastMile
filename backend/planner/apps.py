from django.apps import AppConfig
from django.core import checks


def check_geocoder_provider(app_configs, **kwargs):
    """GEOCODER_PROVIDER must name a known provider (fails ``manage.py check`` / startup otherwise)."""
    from django.conf import settings

    from .geocoder import known_provider_names

    name = getattr(settings, "GEOCODER_PROVIDER", "nominatim")
    if name in known_provider_names():
        return []
    return [
        checks.Error(
            f"Unknown GEOCODER_PROVIDER '{name}'.",
            hint=f"Use one of: {', '.join(sorted(known_provider_names()))}.",
            id="planner.E001",
        )
    ]


class PlannerConfig(AppConfig):
    name = "planner"

    def ready(self):
        checks.register(check_geocoder_provider)
