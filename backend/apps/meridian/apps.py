from django.apps import AppConfig


class MeridianConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.meridian"
    verbose_name = "Meridian"

    def ready(self) -> None:
        from apps.meridian import corner_provider  # noqa: F401
