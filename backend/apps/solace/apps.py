from django.apps import AppConfig


class SolaceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.solace"
    verbose_name = "Solace"

    def ready(self) -> None:
        from apps.solace import handlers
        handlers.connect()
