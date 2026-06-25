from django.apps import AppConfig


class AchievementsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.achievements"
    verbose_name = "Achievements"

    def ready(self) -> None:
        # Connect the event-bus handlers so the app awards badges in response to other
        # nodes' domain events (D4/D20). Import here to avoid app-registry timing issues.
        from apps.achievements import handlers  # noqa: F401

        handlers.connect()
