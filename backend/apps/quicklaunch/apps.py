from django.apps import AppConfig


class QuickLaunchConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.quicklaunch"
    label = "quicklaunch"
    verbose_name = "Quick Launch"

    def ready(self):
        # Importing the target definitions is what populates the registry. Done here so the
        # catalogue is complete for any caller, rather than depending on import order.
        from apps.quicklaunch import targets  # noqa: F401
