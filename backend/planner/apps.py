from django.apps import AppConfig


class PlannerConfig(AppConfig):
    name = "planner"

    def ready(self):
        from . import zones

        zones.warn_if_placeholder()
