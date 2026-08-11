from rest_framework.throttling import UserRateThrottle


class LinkPreviewThrottle(UserRateThrottle):
    """Keep interactive imports useful without letting one login hammer retailers."""

    scope = "link_import_preview"
