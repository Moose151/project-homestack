from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"

    def ready(self) -> None:
        # Connect the event-bus dispatcher (docs/32_Core_Notifications_and_Push.md §7) so other
        # nodes' domain events become notifications without importing their models (D4).
        from apps.notifications import handlers  # noqa: F401

        handlers.connect()
