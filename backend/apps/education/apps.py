from django.apps import AppConfig


class EducationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.education"

    def ready(self) -> None:
        from apps.education import corner_provider  # noqa: F401
