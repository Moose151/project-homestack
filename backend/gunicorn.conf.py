"""Gunicorn configuration for the production HomeStack backend container.

Sized for one household on a home server — a handful of concurrent people, not a public service.
Every value is overridable by environment variable so the live box can be tuned without a rebuild.

Deliberately boring: no Redis, no async worker class, no process supervisor beyond gunicorn's own
master. See docs/02_Software_Architecture_Document.md §15 and docs/34_Recommended_Next_Steps.md §3.
"""
from __future__ import annotations

import os


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")

# Threaded sync workers. A household workload is overwhelmingly I/O-bound (PostgreSQL, the
# occasional outbound link-preview or Web Push call), so a few threads per worker absorb
# concurrency far more cheaply than more processes on a home server's modest RAM.
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "gthread")
workers = _int_env("GUNICORN_WORKERS", 3)
threads = _int_env("GUNICORN_THREADS", 4)

# Generous relative to a normal request, because a few deliberate operations are slow and
# synchronous by design: an on-demand backup shells out to pg_dump, and a link import fetches a
# remote URL. Those should finish, not be killed mid-write.
timeout = _int_env("GUNICORN_TIMEOUT", 120)
graceful_timeout = _int_env("GUNICORN_GRACEFUL_TIMEOUT", 30)

# Nginx Proxy Manager holds client connections; keep gunicorn's keep-alive just above its default
# so idle proxy connections are not churned.
keepalive = _int_env("GUNICORN_KEEPALIVE", 5)

# Recycle workers periodically so any slow leak in a long-lived household process is bounded.
# The jitter stops every worker restarting at the same moment.
max_requests = _int_env("GUNICORN_MAX_REQUESTS", 1000)
max_requests_jitter = _int_env("GUNICORN_MAX_REQUESTS_JITTER", 100)

# Log to stdout/stderr so `docker logs homestack-backend` keeps working exactly as it does today.
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

# NPM sits in front, so its X-Forwarded-For is the only useful client address in the access log.
access_log_format = '%({x-forwarded-for}i)s %(h)s "%(r)s" %(s)s %(b)s %(M)sms "%(a)s"'

# `forwarded_allow_ips` is deliberately left at gunicorn's default (127.0.0.1,::1). Django reads
# the proxy's scheme itself via SECURE_PROXY_SSL_HEADER on the raw header, so HTTPS detection works
# without gunicorn trusting X-Forwarded-* from arbitrary LAN addresses.
