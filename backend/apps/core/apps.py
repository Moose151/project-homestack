from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self) -> None:
        # Registers the production deployment checks (no-ops outside config.settings.prod).
        from apps.core import checks  # noqa: F401
