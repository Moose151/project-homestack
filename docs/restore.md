# HomeStack Backup & Restore Procedure (D17)

Backups consist of two artefacts stored under `BACKUP_DIR` (Docker volume `backup_data`, mounted at `/app/backups` in the backend container):

| File | Contents |
|------|----------|
| `<label>/db.dump` | PostgreSQL custom-format dump (`pg_dump -F c`) |
| `<label>/media.tar.gz` | Tarball of Django `MEDIA_ROOT` |

Both files are SHA-256 checksummed and the hashes are stored in the `backups_backup` DB row. The restore endpoint verifies checksums before touching anything.

---

## 1. Triggering a backup

Via the API (admin session + password re-auth required):

```
POST /api/v1/auth/reauth/   { "password": "..." }
POST /api/v1/backups/
```

The backup runs synchronously and returns `status: "complete"` or `status: "failed"` with `error_message`.

---

## 2. Downloading a backup archive

```
GET /api/v1/backups/<id>/download/
```

Returns a `.tar.gz` containing `db.dump` and `media.tar.gz`. Store this file off-server.

---

## 3. Restoring — step by step

> **Expected downtime:** ~2–5 minutes for a typical household dataset.

### 3a. Put the app in maintenance (stop frontend traffic)

```bash
docker compose stop homestack-frontend homestack-backend
```

### 3b. Copy the backup archive into the backup volume

If you downloaded the archive off-server, copy it back:

```bash
docker cp homestack_backup_YYYYMMDD.tar.gz homestack-backend:/app/backups/
```

Extract it so the directory structure matches what the DB record expects:

```bash
docker exec homestack-backend tar -xzf /app/backups/homestack_backup_YYYYMMDD.tar.gz \
  -C /app/backups/<label>/
```

### 3c. Trigger the restore via API

Start only the backend temporarily:

```bash
docker compose start homestack-backend
```

Re-auth and call the restore endpoint:

```bash
curl -c cookies.txt -b cookies.txt -X POST http://localhost:8000/api/v1/auth/pin-login/ \
  -H 'Content-Type: application/json' -d '{"username":"<admin>","pin":"<pin>"}'

curl -c cookies.txt -b cookies.txt -X POST http://localhost:8000/api/v1/auth/reauth/ \
  -H 'Content-Type: application/json' -d '{"password":"<password>"}'

curl -c cookies.txt -b cookies.txt -X POST http://localhost:8000/api/v1/backups/<id>/restore/ \
  -H 'Content-Type: application/json'
```

The endpoint verifies both SHA-256 checksums, runs `pg_restore --clean --if-exists`, and unpacks the media tarball. A `200 {"detail": "Restore complete."}` response confirms success.

### 3d. Verify data integrity

```bash
# Check that the household row is present
curl -c cookies.txt -b cookies.txt http://localhost:8000/api/v1/household/

# Spot-check a known Atlas list
curl -c cookies.txt -b cookies.txt http://localhost:8000/api/v1/atlas/lists/
```

### 3e. Restart the full stack

```bash
docker compose restart
```

---

## 4. Manual restore (fallback, no API access)

If the backend is broken and you cannot call the API:

```bash
# 1. Restore the DB directly
docker exec -e PGPASSWORD=<password> homestack-postgres \
  pg_restore -h localhost -U homestack -d homestack \
  --clean --if-exists --no-owner /path/to/db.dump

# 2. Unpack media
docker exec homestack-backend \
  tar -xzf /app/backups/<label>/media.tar.gz -C /app/media/ --strip-components=1

# 3. Restart
docker compose restart
```

---

## 5. Checksums

To verify a file manually before restoring:

```bash
sha256sum /path/to/db.dump
sha256sum /path/to/media.tar.gz
```

Compare against `db_checksum` / `media_checksum` in `GET /api/v1/backups/`.
