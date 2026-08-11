from django.apps import AppConfig


class FitnessConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.fitness"

    def ready(self) -> None:
        from apps.fitness import corner_provider  # noqa: F401
