# Production Serving and Deployment

> **Status: implemented, pending live rollout.** This is the canonical contract for how HomeStack
> is served in production and how a deployment is performed, validated and rolled back.
>
> It replaces the previous live path, which ran Django `runserver` and the Vite development server.
> Any older prose describing those as the live servers is stale.

## 1. Outcome

The live household deployment serves the application with production components:

- Django runs under **gunicorn** (`config.wsgi:application`), not `runserver`;
- the React application is a **production Vite build** served by **nginx**, not `vite dev`;
- Django's own static files (admin CSS/JS) are collected at image build time and served by
  **WhiteNoise** from the same gunicorn process;
- development keeps `runserver` and the Vite dev server through an explicit Compose override.

Deliberately **not** part of this change: reducing published container ports, Docker network
redesign, Redis/Celery, CI, or any public exposure. Those remain separately sequenced in
`34_Recommended_Next_Steps.md`.

## 2. Topology

Unchanged from the pre-existing HTTPS deployment — that is the point. Nginx Proxy Manager keeps its
existing routing and needs no reconfiguration.

```text
LAN client
  -> Pi-hole DNS: homestack.moosesoftwares.com -> 192.168.1.125
  -> Nginx Proxy Manager :443   (Let's Encrypt via Cloudflare DNS-01)
       |
       +-- /api/*  -> homestack-backend  :8000   gunicorn -> Django -> PostgreSQL
       |
       +-- /*      -> homestack-frontend :5173   nginx -> built React bundle
```

HomeStack terminates no TLS of its own and adds no second reverse-proxy layer. The frontend
container deliberately does **not** proxy `/api/` — that is NPM's job, and the frontend answers
`/api/` with a clear 404 so a misrouted proxy is obvious rather than returning HTML to a caller
expecting JSON.

Ports are unchanged: gunicorn listens on the container port `runserver` used, and the frontend's
nginx listens on the port the Vite dev server used.

## 3. Compose layout

Production is the **base** file, so the live server's existing `docker compose up -d` keeps
working and now means production.

```bash
# Production (the live server)
docker compose up -d --build

# Development
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

| | Production (`docker-compose.yml`) | Development (`+ docker-compose.dev.yml`) |
|---|---|---|
| Backend command | `gunicorn --config gunicorn.conf.py config.wsgi:application` | `manage.py runserver` |
| Backend settings | `config.settings.prod` | `config.settings.dev` |
| Frontend image target | `production` (nginx + `dist/`) | `development` (Vite dev server) |
| Source | baked into the image | bind-mounted, hot reload |
| Static files | `collectstatic` at build, served by WhiteNoise | Django's `DEBUG=True` handler |
| Health checks | backend + frontend | disabled (reload restarts are noisy) |

`DJANGO_SETTINGS_MODULE` is pinned in each Compose file's `environment:` block, which takes
precedence over `.env`. A stale development value in the live environment file therefore cannot
put the production server back on development settings.

Editing frontend source in development never requires a production image rebuild.

## 4. Backend: gunicorn

Configuration lives in `backend/gunicorn.conf.py`; every value is environment-overridable.

| Setting | Default | Why |
|---|---|---|
| worker class | `gthread` | Household load is I/O-bound; threads are cheaper than processes on a home server |
| workers | 3 | A handful of concurrent people, not a public service |
| threads | 4 | Absorbs concurrency without more Django processes |
| timeout | 120s | On-demand backup shells out to `pg_dump`; link import fetches a remote URL |
| max requests | 1000 (+100 jitter) | Bounds any slow leak in a long-lived process |
| access/error log | stdout/stderr | `docker logs homestack-backend` keeps working unchanged |

`forwarded_allow_ips` is left at gunicorn's default. Django reads the proxy scheme itself through
`SECURE_PROXY_SSL_HEADER`, so HTTPS detection works without gunicorn trusting `X-Forwarded-*` from
arbitrary LAN addresses.

## 5. Frontend: built bundle on nginx

`frontend/Dockerfile` has three stages and two useful targets:

- `development` — Vite dev server;
- `build` — `npm ci` then `npm run build` (which is `tsc && vite build`, so a type error fails the
  image build rather than shipping);
- `production` — `nginx:1.27-alpine` serving `dist/`.

`npm ci` installs exactly the lockfile, so a production image cannot pick up a drifted transitive
version.

`frontend/nginx.conf` provides:

- **SPA fallback** — `/calendar`, `/books`, `/settings/notifications`, `/homestead/...` return the
  application on cold load or refresh;
- **`/sw.js` with `Cache-Control: no-cache`** — a cached service worker would keep handling push
  events after a deploy;
- **`/manifest.json` as `application/manifest+json`** — the location empties the inherited MIME map
  so the correct type applies instead of `application/json` from the `.json` extension;
- **`/assets/` immutable for a year** — Vite content-hashes those filenames;
- **`/brand/` for a day** — referenced by fixed, unhashed names from the manifest and service worker;
- **`index.html` `no-store`** — a deploy is picked up on the next navigation;
- **`/healthz`** for the container health check;
- security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`).

> nginx's `add_header` is inherited only by blocks that define no header of their own. Because
> every location sets its own `Cache-Control`, the security headers are included per-location from
> `nginx-security-headers.conf` rather than declared once at server level, where they would be
> silently dropped. This was found by testing the running container, not by reading the config.

No Content-Security-Policy yet — it has to be authored against the real bundle and verified in a
browser, which is its own change.

## 6. Django static files and admin

`DEBUG=False` stops Django serving `/static/`, which would otherwise leave admin unstyled.

- `collectstatic` runs at **image build time**, so the running container never writes to its own
  image and a deployment cannot forget the step;
- **WhiteNoise** serves `STATIC_ROOT` from the gunicorn process — no second static-server
  architecture for admin alone;
- `CompressedManifestStaticFilesStorage` hashes filenames, so assets cache hard and still update on
  redeploy;
- WhiteNoise serves `STATIC_ROOT` only. Uploads stay behind the permission-checked attachment
  download path (D11) and are never given a static URL.

The build step uses `--skip-checks`: the production deployment checks validate the live `.env`,
which does not exist during a build. They run for real at deploy time (§8).

### Reaching Django admin

Admin and its assets are correct **on the backend**. They are not reachable through the household
HTTPS origin, because NPM routes only `/api/` to the backend — `/admin/` falls through to the SPA.

This is pre-existing behaviour, not a regression, and admin is not part of daily household use.
Note that `DJANGO_SECURE_COOKIES=1` means admin login over plain HTTP on the backend port will not
work either, because the browser will not store a `Secure` session cookie. Turning secure cookies
off is **not** an acceptable workaround.

To use admin over HTTPS, add two locations to the existing NPM proxy host (§10). This is optional.

## 7. Production settings

`config/settings/prod.py` is the live module. Verified behaviour:

- `DEBUG = False`, hardcoded — a leftover `DJANGO_DEBUG=1` in `.env` cannot re-enable it;
- `ALLOWED_HOSTS` from `DJANGO_ALLOWED_HOSTS`, plus `HOMESTACK_PUBLIC_HOSTNAME`, plus
  `localhost`/`127.0.0.1` so the container health check works;
- `CSRF_TRUSTED_ORIGINS` from `DJANGO_CSRF_TRUSTED_ORIGINS`, plus `https://<public hostname>`;
- `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`;
- `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` on unless `DJANGO_SECURE_COOKIES=0`;
- WhiteNoise middleware inserted immediately after `SecurityMiddleware`, by position rather than a
  hardcoded index;
- secrets stay in `.env`, never in the repository or an image layer.

### How CSRF actually behaves behind NPM

Verified against a running gunicorn container rather than assumed: Django accepts a write when the
browser's `Origin` equals the origin it derives from `Host` plus the scheme from
`SECURE_PROXY_SSL_HEADER`. NPM forwards the household hostname unchanged, so **same-origin writes
succeed even with `CSRF_TRUSTED_ORIGINS` empty**, and a foreign origin is still rejected.

Deriving the public hostname is therefore defence in depth, not a prerequisite — which is why an
empty list is a warning, never a deployment-blocking error.

## 8. Deployment configuration checks

`apps/core/checks.py` registers Django system checks that run only under `config.settings.prod`.
Because gunicorn does not run system checks when importing `config.wsgi`, a stale value can never
crash-loop a running container — it surfaces when `manage.py migrate` runs during deployment, which
exits non-zero.

| ID | Level | Condition |
|---|---|---|
| `homestack.E001` | Error | `ALLOWED_HOSTS` names no host beyond loopback |
| `homestack.E003` | Error | `SECRET_KEY` is still the placeholder committed to the repository |
| `homestack.E004` | Error | `DEBUG` is enabled |
| `homestack.W002` | Warning | `CSRF_TRUSTED_ORIGINS` is empty |
| `homestack.W001` | Warning | Session/CSRF cookies are not secure |

## 9. `.env` changes required

**None are strictly required.** The live `.env` already carries everything production needs, and
`DJANGO_SETTINGS_MODULE` is now pinned by Compose regardless of its value.

Recommended while deploying:

```text
DJANGO_CSRF_TRUSTED_ORIGINS=https://homestack.moosesoftwares.com   # explicit; also derived
```

Confirm these are already correct:

```text
DJANGO_SECRET_KEY=<a real generated value, not the repository placeholder>
DJANGO_ALLOWED_HOSTS=...,192.168.1.125,homestack.moosesoftwares.com
HOMESTACK_PUBLIC_HOSTNAME=homestack.moosesoftwares.com
DJANGO_SECURE_COOKIES=1
VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY / VAPID_SUBJECT
```

## 10. Nginx Proxy Manager changes

**None required.** Ports and routing are unchanged.

Optional, only to reach Django admin over HTTPS — add to the existing proxy host's Advanced
configuration, pointing at the same backend upstream `/api/` already uses:

```nginx
location /admin/ {
    proxy_pass http://192.168.1.125:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
location /static/ {
    proxy_pass http://192.168.1.125:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Do not add router port forwarding. Do not terminate TLS inside HomeStack.

## 11. Deployment

### 11.1 Back up first

Backups are triggered through the application, not a management command (`docs/restore.md` §1):
sign in as an admin and `POST /api/v1/backups/`, or use the Manage HomeStack backup action. The
run is synchronous and returns `status: "complete"`.

Then record the commit to roll back to, and confirm the artefacts landed:

```bash
cd /opt/docker/project-homestack
git rev-parse HEAD > /tmp/homestack-rollback-commit.txt            # the known-good commit
cat /tmp/homestack-rollback-commit.txt

docker exec homestack-backend ls -lh /app/backups | tail -5        # recent db + media artefacts
```

Do not continue without a recent, complete backup. See `docs/restore.md` for verification and the
restore path itself.

### 11.2 Deploy

```bash
cd /opt/docker/project-homestack
git fetch origin
git checkout main && git pull

docker compose build homestack-backend homestack-frontend
docker compose up -d

# Runs the production deployment checks; exits non-zero on a misconfigured environment.
docker exec homestack-backend python manage.py migrate
```

This change adds no migrations, but `migrate` is what runs the configuration checks, so do not
skip it.

### 11.3 Smoke test

Run §12 before considering the deployment done.

## 12. Live smoke-test checklist

```bash
# 1. containers up and healthy
docker compose ps

# 2. backend health (container-internal and through HTTPS)
docker exec homestack-backend python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/',timeout=5).status)"
curl -fsS https://homestack.moosesoftwares.com/api/v1/health/; echo

# 3. HTTPS frontend loads
curl -fsS -o /dev/null -w '%{http_code}\n' https://homestack.moosesoftwares.com/

# 11. deep-link refresh returns the app, not a 404
for p in /calendar /books /settings/notifications /homestead; do
  printf '%s -> %s\n' "$p" "$(curl -s -o /dev/null -w '%{http_code}' https://homestack.moosesoftwares.com$p)"
done

# 12. service worker and PWA assets
curl -sI https://homestack.moosesoftwares.com/sw.js | head -1
curl -sI https://homestack.moosesoftwares.com/manifest.json | head -1
curl -sI https://homestack.moosesoftwares.com/brand/mark-192.png | head -1

# 16. Django admin assets (on the backend; HTTPS only if the optional NPM locations were added)
docker exec homestack-backend python -c "import urllib.request;r=urllib.request.urlopen('http://127.0.0.1:8000/admin/login/',timeout=5);print(r.status,len(r.read()))"

# 17. scheduled notification command still runs
docker exec homestack-backend python manage.py notifications_run_scheduled && echo OK

# gunicorn is actually what is serving
docker logs --tail=20 homestack-backend | grep -i gunicorn
```

In a browser at `https://homestack.moosesoftwares.com`:

| # | Check |
|---|---|
| 4 | Password login succeeds |
| 5 | Avatar/PIN login succeeds |
| 6 | Logout, then log back in |
| 7 | Authenticated write — create and edit an Atlas item, and confirm it persists after reload |
| 8 | Calendar loads and an event opens |
| 9 | A sensitive node demands password re-authentication |
| 10 | Solace opens after re-authentication |
| 11 | Refresh directly on a deep link such as `/settings/notifications` |
| 12 | DevTools → Application → Service Workers shows `sw.js` **activated**, scope `/` |
| 13 | Notification settings lists the previously registered devices |
| 14 | "Test" on a device delivers a push |
| 15 | With HomeStack unfocused, a push arrives and clicking it opens the right deep link |

Push subscriptions live in PostgreSQL, keyed by browser endpoint, so recreating the backend or
frontend container does not invalidate them. The service worker re-registers on next load; because
`/sw.js` is served `no-cache`, an updated worker is picked up rather than a stale copy.

## 13. Rollback

Rollback is "check out the previous commit and rebuild" — no data migration is involved and this
change adds no migrations, so nothing has to be undone in the database.

```bash
cd /opt/docker/project-homestack
git checkout "$(cat /tmp/homestack-rollback-commit.txt)"     # the pre-deployment commit
docker compose build homestack-backend homestack-frontend
docker compose up -d --force-recreate
curl -fsS https://homestack.moosesoftwares.com/api/v1/health/; echo
```

Symptom-specific guidance:

| Symptom | Likely cause | Action |
|---|---|---|
| Backend restarts repeatedly | gunicorn cannot import the app, or PostgreSQL unreachable | `docker logs homestack-backend`; check `.env` database values |
| `migrate` exits non-zero with `homestack.E0xx` | Live `.env` is missing a production value | Fix `.env` per §9, re-run `migrate`. Do not skip the check |
| App loads, every save fails CSRF | NPM is not forwarding the household `Host` | Set `DJANGO_CSRF_TRUSTED_ORIGINS`, recreate the backend |
| Login appears to succeed then immediately logs out | Secure cookie over a non-HTTPS origin | Use the HTTPS hostname, not the LAN IP and port |
| Frontend 404s on refresh of a deep link | Frontend image is not the `production` target | Rebuild `homestack-frontend`; confirm `docker compose ps` |
| Frontend returns 404 JSON for `/api/` | NPM `/api/` route is missing or misdirected | Restore the NPM `/api/` location |
| Admin unstyled | `collectstatic` did not run | Rebuild the backend image rather than running it in the container |

Because the frontend is a static bundle and the backend is stateless between requests, rolling back
does not lose household data. Push subscriptions, sessions and all records live in PostgreSQL.

## 14. Follow-ups deliberately not in this change

- reduce published host ports and put PostgreSQL on an internal-only network
  (`34_Recommended_Next_Steps.md` §4);
- one supported `./scripts/deploy.sh` that performs the §11/§12 sequence (§5 there);
- frontend unit/E2E tests and CI (§6 there);
- a Content-Security-Policy for the frontend, authored against the real bundle;
- Django admin over HTTPS by default, if the optional NPM locations prove worth standardising.
