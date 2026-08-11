from django.apps import AppConfig


class HomesteadConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.homestead"

    def ready(self) -> None:
        from apps.homestead import corner_provider, handlers  # noqa: F401
        handlers.connect()
