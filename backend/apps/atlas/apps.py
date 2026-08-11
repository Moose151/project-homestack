from django.apps import AppConfig


class AtlasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.atlas"

    def ready(self) -> None:
        from apps.atlas import corner_provider  # noqa: F401
