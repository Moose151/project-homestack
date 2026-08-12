FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# postgresql-client is here for Phase 1.11 backups (pg_dump / pg_restore).
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect Django admin's CSS/JS into STATIC_ROOT for WhiteNoise to serve, since DEBUG=False stops
# Django serving them itself. Done at build time so the running container never writes to its own
# image and a deployment cannot forget the step.
#
# `--skip-checks` because the production deployment checks (apps/core/checks.py) validate the live
# .env — allowed hosts, CSRF origins, a real secret key — none of which exist during a build, and
# satisfying them with placeholders would prove nothing. They run for real at deploy time, when
# `manage.py migrate` executes against the actual environment. collectstatic itself reads no
# secret and touches no database.
RUN DJANGO_SETTINGS_MODULE=config.settings.prod \
    DJANGO_SECRET_KEY=build-time-only-never-used-at-runtime \
    python manage.py collectstatic --noinput --clear --skip-checks

EXPOSE 8000

# Production default. The development override (docker-compose.dev.yml) replaces this with
# `runserver` for autoreload; nothing else should run runserver.
CMD ["gunicorn", "--config", "gunicorn.conf.py", "config.wsgi:application"]
