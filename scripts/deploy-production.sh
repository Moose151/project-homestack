#!/usr/bin/env bash
set -Eeuo pipefail

# HomeStack safe production deployment script.
#
# Intended live usage:
#   cd /opt/docker/project-homestack
#   ./scripts/deploy-production.sh [--migrate] [--dry-run]
#
# This script deliberately avoids destructive Docker/Git cleanup. It never runs compose down,
# prunes, deletes volumes, resets Git, or flushes the database.

COMPOSE_PROJECT_DIR="${COMPOSE_PROJECT_DIR:-/opt/docker/project-homestack}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-project-homestack}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://homestack.moosesoftwares.com}"
NPM_CONTAINER="${NPM_CONTAINER:-nginx-proxy-manager}"
NPM_NETWORK="${NPM_NETWORK:-proxy}"
PRIVATE_NETWORK="${PRIVATE_NETWORK:-project-homestack_private}"
BACKUP_MAX_AGE_HOURS="${BACKUP_MAX_AGE_HOURS:-24}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-180}"
HEALTH_INTERVAL="${HEALTH_INTERVAL:-5}"
LOG_TAIL_LINES="${LOG_TAIL_LINES:-80}"
DEPLOYED_SHA_FILE="${DEPLOYED_SHA_FILE:-.git/homestack-deployed-sha}"

BACKEND_SERVICE="${BACKEND_SERVICE:-homestack-backend}"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-homestack-frontend}"
POSTGRES_SERVICE="${POSTGRES_SERVICE:-homestack-postgres}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-homestack-backend}"
FRONTEND_CONTAINER="${FRONTEND_CONTAINER:-homestack-frontend}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-homestack-postgres}"

REQUIRED_SERVICES=("$POSTGRES_SERVICE" "$BACKEND_SERVICE" "$FRONTEND_SERVICE")
REQUIRED_VOLUMES=(
  "${COMPOSE_PROJECT_NAME}_postgres_data"
  "${COMPOSE_PROJECT_NAME}_media_data"
  "${COMPOSE_PROJECT_NAME}_backup_data"
)

RUN_MIGRATIONS=0
SKIP_BACKUP_AGE_CHECK=0
DRY_RUN=0
BOOTSTRAP_DEPLOYED_SHA=""
RECORD_ROLLBACK_SHA=""
PHASE="startup"
CHECKOUT_SHA=""
TARGET_SHA=""
DEPLOYED_SHA=""
ROLLBACK_SHA=""
BACKUP_DIR_USED=""
NPM_RELOADED=0

usage() {
  cat <<'USAGE'
Usage: scripts/deploy-production.sh [options]

Options:
  --migrate                 Run reviewed Django migrations from the newly built backend image.
  --skip-backup-age-check   Emergency/manual use only: require complete backup files but ignore age.
  --dry-run                 Run preflight and backup inspection only; do not fetch/build/recreate/reload.
  --bootstrap-deployed-sha SHA
                            First-time setup only: record the SHA already running in production.
                            Fails if a deployed SHA marker already exists.
  --record-rollback-sha SHA
                            Manual-rollback correction only: after a manual rollback has been
                            built, promoted and fully validated (see
                            docs/35_Production_Serving_and_Deployment.md section 13), atomically
                            record that rollback commit as the deployed SHA marker. Does not
                            fetch, build, migrate, recreate containers, reload NPM, or move the
                            Git checkout.
  --help                    Show this help.

Normal deployment:
  cd /opt/docker/project-homestack
  ./scripts/deploy-production.sh

Deployment with reviewed migrations:
  ./scripts/deploy-production.sh --migrate

Environment overrides:
  COMPOSE_PROJECT_DIR, COMPOSE_PROJECT_NAME, NPM_CONTAINER, NPM_NETWORK, PUBLIC_BASE_URL,
  BACKUP_MAX_AGE_HOURS, HEALTH_TIMEOUT, HEALTH_INTERVAL, DEPLOYED_SHA_FILE.
USAGE
}

log() { printf '\n[%s] %s\n' "$PHASE" "$*"; }
info() { printf '  - %s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*" >&2; }
fail() { printf 'ERROR [%s]: %s\n' "$PHASE" "$*" >&2; exit 1; }

on_error() {
  local exit_code=$?
  printf '\nDeployment stopped in phase: %s\n' "$PHASE" >&2
  printf 'Exit code: %s\n' "$exit_code" >&2
  if [[ -n "${ROLLBACK_SHA:-}" ]]; then
    printf 'Rollback SHA: %s\n' "$ROLLBACK_SHA" >&2
    printf 'See docs/35_Production_Serving_and_Deployment.md for the manual rollback procedure.\n' >&2
  fi
}
trap on_error ERR

compose() { docker compose "$@"; }

parse_args() {
  while (($#)); do
    case "$1" in
      --migrate) RUN_MIGRATIONS=1 ;;
      --skip-backup-age-check) SKIP_BACKUP_AGE_CHECK=1 ;;
      --dry-run) DRY_RUN=1 ;;
      --bootstrap-deployed-sha)
        shift
        [[ $# -gt 0 ]] || fail "--bootstrap-deployed-sha requires a commit SHA"
        BOOTSTRAP_DEPLOYED_SHA="$1"
        ;;
      --record-rollback-sha)
        shift
        [[ $# -gt 0 ]] || fail "--record-rollback-sha requires a commit SHA"
        RECORD_ROLLBACK_SHA="$1"
        ;;
      --help) usage; exit 0 ;;
      *) fail "Unknown option: $1" ;;
    esac
    shift
  done
}

require_valid_commit() {
  local sha="$1"
  git rev-parse --verify --quiet "$sha^{commit}" >/dev/null || fail "Commit SHA is not present in this repository: $sha"
}

# Resolves any commit-ish (abbreviated SHA, tag, ref) to the canonical full commit SHA, so
# marker reads/writes and comparisons never depend on abbreviation length.
resolve_full_sha() {
  local ref="$1"
  require_valid_commit "$ref"
  git rev-parse --verify --quiet "${ref}^{commit}"
}

read_deployed_sha() {
  if [[ ! -f "$DEPLOYED_SHA_FILE" ]]; then
    fail "No deployed SHA marker found at $DEPLOYED_SHA_FILE. Bootstrap once with: ./scripts/deploy-production.sh --bootstrap-deployed-sha <sha-currently-running-in-production>"
  fi
  local sha
  sha="$(tr -d '[:space:]' < "$DEPLOYED_SHA_FILE")"
  [[ -n "$sha" ]] || fail "Deployed SHA marker is empty: $DEPLOYED_SHA_FILE"
  resolve_full_sha "$sha"
}

write_deployed_sha() {
  local sha="$1"
  local full_sha
  full_sha="$(resolve_full_sha "$sha")"
  local tmp="${DEPLOYED_SHA_FILE}.tmp"
  printf '%s\n' "$full_sha" > "$tmp"
  mv "$tmp" "$DEPLOYED_SHA_FILE"
}

# Fails closed unless the recorded deployed SHA is genuinely part of target's history (or equal
# to it). A marker pointing at an unrelated/non-ancestor commit means deployment-state tracking
# itself is untrustworthy, so this must never be silently skipped.
require_deployed_sha_lineage() {
  [[ "$DEPLOYED_SHA" == "$TARGET_SHA" ]] && return 0
  git merge-base --is-ancestor "$DEPLOYED_SHA" "$TARGET_SHA" || \
    fail "Deployed SHA marker ($DEPLOYED_SHA) is not an ancestor of target SHA ($TARGET_SHA). Deployed-state lineage is inconsistent with origin/main history in $DEPLOYED_SHA_FILE and requires manual inspection before deploying."
}

bootstrap_deployed_sha() {
  PHASE="bootstrap deployed SHA"
  require_repo_dir
  require_branch_main
  require_clean_tree
  [[ -n "$BOOTSTRAP_DEPLOYED_SHA" ]] || fail "No bootstrap SHA supplied"
  [[ ! -f "$DEPLOYED_SHA_FILE" ]] || fail "Deployed SHA marker already exists at $DEPLOYED_SHA_FILE"
  local full_sha
  full_sha="$(resolve_full_sha "$BOOTSTRAP_DEPLOYED_SHA")"
  write_deployed_sha "$full_sha"
  printf 'Recorded deployed SHA marker: %s\n' "$full_sha"
  printf 'Marker file: %s\n' "$DEPLOYED_SHA_FILE"
  printf 'No deployment was performed.\n'
}

# Manual-rollback correction: run only after a rollback has been checked out, built, promoted and
# fully validated by hand (docs/35_Production_Serving_and_Deployment.md section 13). This never
# runs implicitly and never runs before that validation, so the marker cannot advance past a
# rollback that has not actually been proven healthy. It does not touch containers or the checkout.
record_rollback_deployed_sha() {
  PHASE="record rollback deployed SHA"
  require_repo_dir
  require_clean_tree
  [[ -n "$RECORD_ROLLBACK_SHA" ]] || fail "No rollback SHA supplied"
  [[ -f "$DEPLOYED_SHA_FILE" ]] || fail "No deployed SHA marker found at $DEPLOYED_SHA_FILE. Use --bootstrap-deployed-sha for first-time setup instead."
  local full_sha
  full_sha="$(resolve_full_sha "$RECORD_ROLLBACK_SHA")"
  write_deployed_sha "$full_sha"
  printf 'Recorded rollback commit as the deployed SHA marker: %s\n' "$full_sha"
  printf 'Marker file: %s\n' "$DEPLOYED_SHA_FILE"
  printf 'No fetch, build, migration, container recreation, NPM reload, or checkout change was performed.\n'
  printf 'Only the next normal deploy will act on this marker.\n'
}

require_repo_dir() {
  [[ -d "$COMPOSE_PROJECT_DIR/.git" ]] || fail "Repository not found at $COMPOSE_PROJECT_DIR"
  [[ -f "$COMPOSE_PROJECT_DIR/docker-compose.yml" ]] || fail "docker-compose.yml not found at $COMPOSE_PROJECT_DIR"
  cd "$COMPOSE_PROJECT_DIR"
  local top
  top="$(git rev-parse --show-toplevel)"
  [[ "$top" == "$COMPOSE_PROJECT_DIR" ]] || fail "Refusing to run outside repository root: $top"
}

require_branch_main() {
  local branch
  branch="$(git rev-parse --abbrev-ref HEAD)"
  [[ "$branch" == "main" ]] || fail "Current branch is '$branch'; production deploys must run from main"
}

require_clean_tree() {
  [[ -z "$(git status --porcelain)" ]] || fail "Git working tree is dirty; commit or stash changes before deploying"
}

git_ahead_behind() {
  git rev-list --left-right --count HEAD...origin/main
}

require_origin_reachable() {
  git ls-remote --exit-code origin HEAD >/dev/null || fail "origin is not reachable"
}

require_main_not_ahead_or_diverged() {
  local ahead behind
  read -r ahead behind < <(git_ahead_behind)
  if (( ahead > 0 && behind > 0 )); then
    fail "Local main and origin/main have diverged; resolve manually"
  fi
  if (( ahead > 0 )); then
    fail "Local main is ahead of origin/main; push/review that work before production deploy"
  fi
}

require_tools() {
  command -v git >/dev/null || fail "git is not available"
  command -v docker >/dev/null || fail "docker is not available"
  docker info >/dev/null || fail "Docker daemon is not available"
  docker compose version >/dev/null || fail "Docker Compose is not available"
  command -v curl >/dev/null || fail "curl is not available"
}

require_compose_config() {
  compose config --quiet || fail "docker compose config did not validate"
  local services
  services="$(compose config --services)"
  local service
  for service in "${REQUIRED_SERVICES[@]}"; do
    grep -qx "$service" <<<"$services" || fail "Compose service '$service' is missing"
  done
}

require_network_exists() {
  docker network inspect "$NPM_NETWORK" >/dev/null || fail "Docker network '$NPM_NETWORK' is missing"
}

require_container_running() {
  local container="$1"
  local running
  running="$(docker inspect -f '{{.State.Running}}' "$container" 2>/dev/null || true)"
  [[ "$running" == "true" ]] || fail "Container '$container' is not running"
}

container_health() {
  local container="$1"
  docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{if .State.Running}}running{{else}}stopped{{end}}{{end}}' "$container"
}

require_container_healthy() {
  local container="$1"
  local status
  status="$(container_health "$container" 2>/dev/null || true)"
  [[ "$status" == "healthy" ]] || fail "Container '$container' is '$status', expected healthy"
}

require_starting_stack_healthy() {
  require_container_running "$NPM_CONTAINER"
  require_container_healthy "$POSTGRES_CONTAINER"
  require_container_healthy "$BACKEND_CONTAINER"
  require_container_healthy "$FRONTEND_CONTAINER"
}

require_volumes_exist() {
  local volume
  for volume in "${REQUIRED_VOLUMES[@]}"; do
    docker volume inspect "$volume" >/dev/null || fail "Required Docker volume '$volume' is missing"
  done
}

docker_port_output() {
  local container="$1"
  local port="$2"
  docker port "$container" "$port/tcp" 2>/dev/null || true
}

require_no_published_port() {
  local container="$1"
  local port="$2"
  local output
  output="$(docker_port_output "$container" "$port")"
  [[ -z "$output" ]] || fail "$container publishes host port for $port/tcp: $output"
}

require_no_sensitive_host_ports() {
  require_no_published_port "$POSTGRES_CONTAINER" 5432
  require_no_published_port "$BACKEND_CONTAINER" 8000
  require_no_published_port "$FRONTEND_CONTAINER" 5173
}

container_networks() {
  docker inspect "$1" --format '{{range $name, $_ := .NetworkSettings.Networks}}{{println $name}}{{end}}'
}

require_network_membership_exact() {
  local container="$1"
  shift
  local expected=("$@")
  local actual
  actual="$(container_networks "$container" | sort)"
  local wanted
  wanted="$(printf '%s\n' "${expected[@]}" | sort)"
  [[ "$actual" == "$wanted" ]] || fail "$container networks are [$actual], expected [$wanted]"
}

require_topology() {
  require_network_membership_exact "$FRONTEND_CONTAINER" "$NPM_NETWORK"
  require_network_membership_exact "$BACKEND_CONTAINER" "$NPM_NETWORK" "$PRIVATE_NETWORK"
  require_network_membership_exact "$POSTGRES_CONTAINER" "$PRIVATE_NETWORK"
  require_no_sensitive_host_ports
}

backup_epoch_from_name() {
  local name="${1##*/}"
  [[ "$name" =~ ^backup_([0-9]{8})_([0-9]{6})$ ]] || return 1
  local date_part="${BASH_REMATCH[1]}"
  local time_part="${BASH_REMATCH[2]}"
  date -u -d "${date_part:0:4}-${date_part:4:2}-${date_part:6:2} ${time_part:0:2}:${time_part:2:2}:${time_part:4:2} UTC" +%s
}

newest_backup_dir() {
  docker exec "$BACKEND_CONTAINER" sh -c \
    "find /app/backups -mindepth 1 -maxdepth 1 -type d -name 'backup_*' -print 2>/dev/null | sort | tail -n 1"
}

require_recent_backup() {
  local backup_dir
  backup_dir="$(newest_backup_dir)"
  [[ -n "$backup_dir" ]] || fail "No HomeStack backup directory found in /app/backups"
  local epoch now max_age_seconds age
  epoch="$(backup_epoch_from_name "$backup_dir")" || fail "Newest backup has unexpected name: $backup_dir"
  now="$(date -u +%s)"
  max_age_seconds=$((BACKUP_MAX_AGE_HOURS * 3600))
  age=$((now - epoch))
  if (( SKIP_BACKUP_AGE_CHECK == 0 && age > max_age_seconds )); then
    fail "Newest backup is older than ${BACKUP_MAX_AGE_HOURS}h: $backup_dir. Create a HomeStack backup before retrying."
  fi
  docker exec "$BACKEND_CONTAINER" test -s "$backup_dir/db.dump" || fail "Backup is incomplete: missing/empty db.dump in $backup_dir"
  docker exec "$BACKEND_CONTAINER" test -s "$backup_dir/media.tar.gz" || fail "Backup is incomplete: missing/empty media.tar.gz in $backup_dir"
  BACKUP_DIR_USED="$backup_dir"
  if (( SKIP_BACKUP_AGE_CHECK == 1 )); then
    warn "--skip-backup-age-check used. Backup completeness was checked, but age was ignored."
  fi
  info "Backup gate passed: $BACKUP_DIR_USED"
}

preflight() {
  PHASE="phase 1: preflight"
  log "Checking repository, Docker, Compose, running containers and hardened topology"
  require_repo_dir
  require_branch_main
  require_clean_tree
  require_tools
  if (( DRY_RUN == 0 )); then
    require_origin_reachable
  fi
  require_main_not_ahead_or_diverged
  require_compose_config
  require_network_exists
  require_starting_stack_healthy
  require_volumes_exist
  require_topology
  CHECKOUT_SHA="$(git rev-parse HEAD)"
  DEPLOYED_SHA="$(read_deployed_sha)"
  ROLLBACK_SHA="$DEPLOYED_SHA"
  info "Checkout SHA: $CHECKOUT_SHA"
  info "Last deployed SHA: $DEPLOYED_SHA"
  info "Rollback SHA captured: $ROLLBACK_SHA"
}

backup_gate() {
  PHASE="phase 2: backup gate"
  log "Checking newest HomeStack backup"
  require_recent_backup
}

git_update() {
  PHASE="phase 3: git update"
  log "Fetching origin and fast-forwarding main only"
  git fetch origin
  require_main_not_ahead_or_diverged
  TARGET_SHA="$(git rev-parse origin/main)"
  info "Checkout SHA: $CHECKOUT_SHA"
  info "Target SHA:   $TARGET_SHA"
  info "Deployed SHA: $DEPLOYED_SHA"
  info "Rollback SHA: $ROLLBACK_SHA"
  require_deployed_sha_lineage
  if [[ "$TARGET_SHA" == "$DEPLOYED_SHA" ]]; then
    if [[ "$CHECKOUT_SHA" != "$TARGET_SHA" ]]; then
      log "Production is already up to date; fast-forwarding local checkout only"
      git merge --ff-only origin/main
      CHECKOUT_SHA="$(git rev-parse HEAD)"
    fi
    no_op_summary
    exit 0
  fi
  git merge --ff-only origin/main
  CHECKOUT_SHA="$(git rev-parse HEAD)"
}

dry_run_target_summary() {
  PHASE="dry run target inspection"
  TARGET_SHA="$(git rev-parse origin/main)"
  log "Dry run uses locally cached origin/main; it does not fetch"
  info "Checkout SHA: $CHECKOUT_SHA"
  info "Cached target SHA: $TARGET_SHA"
  info "Recorded deployed SHA: $DEPLOYED_SHA"
  if [[ "$TARGET_SHA" == "$DEPLOYED_SHA" ]]; then
    info "A live run would be a no-op because cached origin/main equals the deployed marker."
  else
    info "A live run would attempt to deploy cached origin/main after fetching and rechecking Git state."
  fi
}

build_images() {
  PHASE="phase 4: build before touching production"
  if (( DRY_RUN == 1 )); then
    log "Dry run: skipping image build"
    return
  fi
  log "Building backend and frontend images before promotion"
  compose build "$BACKEND_SERVICE" "$FRONTEND_SERVICE"
}

changed_migration_files() {
  git diff --name-only "$ROLLBACK_SHA" "$TARGET_SHA" -- 'backend/**/migrations/*.py' \
    | grep -v '/__init__\.py$' || true
}

migration_phase() {
  PHASE="phase 5: database migration handling"
  if (( DRY_RUN == 1 )); then
    log "Dry run: skipping Django check/migration inspection"
    return
  fi
  log "Running production Django checks from the newly built backend image"
  compose run --rm --no-deps "$BACKEND_SERVICE" python manage.py check
  local changed_migrations
  changed_migrations="$(changed_migration_files)"
  if [[ -n "$changed_migrations" && "$RUN_MIGRATIONS" -eq 0 ]]; then
    warn "Migration files changed in this deploy, but --migrate was not supplied:"
    printf '%s\n' "$changed_migrations" >&2
  fi
  if (( RUN_MIGRATIONS == 1 )); then
    log "Checking pending migrations, then applying reviewed migrations"
    compose run --rm --no-deps "$BACKEND_SERVICE" python manage.py showmigrations --plan >/dev/null
    compose run --rm --no-deps "$BACKEND_SERVICE" python manage.py migrate --noinput
  else
    log "Verifying no unapplied migrations are pending"
    compose run --rm --no-deps "$BACKEND_SERVICE" python manage.py migrate --check
  fi
}

wait_for_healthy() {
  local container="$1"
  local deadline=$((SECONDS + HEALTH_TIMEOUT))
  local status
  while (( SECONDS < deadline )); do
    status="$(container_health "$container" 2>/dev/null || true)"
    if [[ "$status" == "healthy" ]]; then
      info "$container is healthy"
      return 0
    fi
    if [[ "$status" == "unhealthy" || "$status" == "stopped" ]]; then
      docker logs --tail="$LOG_TAIL_LINES" "$container" >&2 || true
      fail "$container became $status"
    fi
    sleep "$HEALTH_INTERVAL"
  done
  docker logs --tail="$LOG_TAIL_LINES" "$container" >&2 || true
  fail "Timed out waiting for $container to become healthy"
}

reload_npm() {
  docker exec "$NPM_CONTAINER" nginx -t || fail "NPM nginx configuration test failed; reload was not attempted"
  docker exec "$NPM_CONTAINER" nginx -s reload || fail "NPM nginx reload failed"
  NPM_RELOADED=1
}

validate_api_https() {
  curl -fsS "${PUBLIC_BASE_URL%/}/api/v1/health/" >/dev/null
}

validate_frontend_https() {
  curl -fsS -o /dev/null "${PUBLIC_BASE_URL%/}/"
}

validate_backend_db_connection() {
  docker exec "$BACKEND_CONTAINER" python manage.py shell -c \
    "from django.db import connection; connection.ensure_connection(); print('db-ok')" >/dev/null
}

deploy_backend() {
  PHASE="phase 6: controlled backend deployment"
  if (( DRY_RUN == 1 )); then
    log "Dry run: skipping backend recreation"
    return
  fi
  log "Recreating backend only"
  compose up -d --no-deps --force-recreate "$BACKEND_SERVICE"
  wait_for_healthy "$BACKEND_CONTAINER"
}

validate_backend() {
  PHASE="phase 7: NPM reload and backend validation"
  if (( DRY_RUN == 1 )); then
    log "Dry run: skipping NPM reload and backend HTTPS/DB checks"
    return
  fi
  log "Testing/reloading NPM and validating backend/API"
  reload_npm
  validate_api_https
  validate_backend_db_connection
}

deploy_frontend() {
  PHASE="phase 8: controlled frontend deployment"
  if (( DRY_RUN == 1 )); then
    log "Dry run: skipping frontend recreation and NPM reload"
    return
  fi
  log "Recreating frontend only"
  compose up -d --no-deps --force-recreate "$FRONTEND_SERVICE"
  wait_for_healthy "$FRONTEND_CONTAINER"
  reload_npm
  validate_frontend_https
}

final_validation() {
  PHASE="phase 9: final security/network validation"
  log "Checking final health and hardened Docker topology"
  require_container_healthy "$POSTGRES_CONTAINER"
  require_container_healthy "$BACKEND_CONTAINER"
  require_container_healthy "$FRONTEND_CONTAINER"
  require_topology
}

completion_summary() {
  local migrations="$1"
  local deploy_status="${2:-completed}"
  PHASE="phase 10: completion summary"
  cat <<SUMMARY

HomeStack production deployment successful

Previous SHA: ${ROLLBACK_SHA:-unknown}
Deployed SHA: ${TARGET_SHA:-$ROLLBACK_SHA}
Rollback SHA: ${ROLLBACK_SHA:-unknown}
Backend: healthy
Frontend: healthy
PostgreSQL: healthy
HTTPS frontend: ${deploy_status}
HTTPS API: ${deploy_status}
NPM: $([[ "$NPM_RELOADED" -eq 1 ]] && printf 'reloaded' || printf 'not reloaded')
Direct host ports: closed
Backup used for safety check: ${BACKUP_DIR_USED:-not checked}
Migrations: $migrations
SUMMARY
}

no_op_summary() {
  PHASE="phase 3: no-op"
  cat <<SUMMARY

HomeStack production deployment not needed

Target SHA: ${TARGET_SHA:-unknown}
Recorded deployed SHA: ${DEPLOYED_SHA:-unknown}
Checkout SHA: ${CHECKOUT_SHA:-unknown}

No containers were recreated and the deployed SHA marker was not changed.
SUMMARY
}

main() {
  parse_args "$@"
  if [[ -n "$BOOTSTRAP_DEPLOYED_SHA" ]]; then
    bootstrap_deployed_sha
    exit 0
  fi
  if [[ -n "$RECORD_ROLLBACK_SHA" ]]; then
    record_rollback_deployed_sha
    exit 0
  fi
  if (( SKIP_BACKUP_AGE_CHECK == 1 )); then
    warn "Emergency override enabled: backup age will not block deployment."
  fi
  preflight
  backup_gate
  if (( DRY_RUN == 1 )); then
    dry_run_target_summary
    PHASE="dry run complete"
    log "Dry run completed. No git fetch, build, migration, container recreation, or NPM reload was performed."
    exit 0
  fi
  git_update
  build_images
  migration_phase
  deploy_backend
  validate_backend
  deploy_frontend
  final_validation
  PHASE="phase 10: record deployed SHA"
  log "Recording successfully deployed SHA"
  write_deployed_sha "$TARGET_SHA"
  DEPLOYED_SHA="$TARGET_SHA"
  completion_summary "$([[ "$RUN_MIGRATIONS" -eq 1 ]] && printf 'completed' || printf 'not run')" "OK"
}

if [[ "${HOMESTACK_DEPLOY_LIB_ONLY:-0}" != "1" ]]; then
  main "$@"
fi
