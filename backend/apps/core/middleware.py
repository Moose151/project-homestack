"""Small response-time instrumentation for API diagnostics."""
from __future__ import annotations

import logging
from time import perf_counter

logger = logging.getLogger("homestack.performance")


class RequestTimingMiddleware:
    """Expose request duration in Server-Timing and log unusually slow API calls."""

    slow_request_ms = 500

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = perf_counter()
        response = self.get_response(request)
        duration_ms = (perf_counter() - started) * 1000
        if request.path.startswith("/api/"):
            response["Server-Timing"] = f"app;dur={duration_ms:.1f}"
            if duration_ms >= self.slow_request_ms:
                logger.warning(
                    "Slow API request method=%s path=%s status=%s duration_ms=%.1f",
                    request.method,
                    request.path,
                    response.status_code,
                    duration_ms,
                )
        return response
