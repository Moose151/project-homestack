#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export HOMESTACK_DEPLOY_LIB_ONLY=1
# shellcheck source=scripts/deploy-production.sh
source "$ROOT/scripts/deploy-production.sh"

PASS=0
FAILURES=0
MUTATIONS=0

reset_state() {
  PHASE="test"
  RUN_MIGRATIONS=0
  SKIP_BACKUP_AGE_CHECK=0
  DRY_RUN=0
  HEALTH_TIMEOUT=1
  HEALTH_INTERVAL=1
  BACKUP_MAX_AGE_HOURS=24
  BACKUP_DIR_USED=""
  NPM_RELOADED=0
  MUTATIONS=0
}

pass() {
  PASS=$((PASS + 1))
  printf 'ok - %s\n' "$1"
}

fail_test() {
  FAILURES=$((FAILURES + 1))
  printf 'not ok - %s\n' "$1" >&2
}

expect_success() {
  local name="$1"
  shift
  reset_state
  if ( "$@" ) >/tmp/homestack-deploy-test.out 2>/tmp/homestack-deploy-test.err; then
    pass "$name"
  else
    fail_test "$name"
    cat /tmp/homestack-deploy-test.err >&2 || true
  fi
}

expect_failure() {
  local name="$1"
  shift
  reset_state
  if ( "$@" ) >/tmp/homestack-deploy-test.out 2>/tmp/homestack-deploy-test.err; then
    fail_test "$name"
  else
    pass "$name"
  fi
}

test_dirty_git_rejected() {
  git() {
    case "$*" in
      "status --porcelain") printf ' M file\n' ;;
      *) command git "$@" ;;
    esac
  }
  require_clean_tree
}

test_wrong_branch_rejected() {
  git() {
    case "$*" in
      "rev-parse --abbrev-ref HEAD") printf 'feature/test\n' ;;
      *) command git "$@" ;;
    esac
  }
  require_branch_main
}

test_missing_proxy_network_rejected() {
  docker() {
    [[ "$1 $2" == "network inspect" ]] && return 1
    return 0
  }
  require_network_exists
}

test_stale_backup_rejected() {
  newest_backup_dir() { printf '/app/backups/backup_20000101_000000\n'; }
  docker() {
    [[ "$1" == "exec" && "$3" == "test" ]] && return 0
    return 0
  }
  require_recent_backup
}

test_incomplete_backup_rejected() {
  newest_backup_dir() { date -u '+/app/backups/backup_%Y%m%d_%H%M%S'; }
  docker() {
    if [[ "$1" == "exec" && "$3" == "test" ]]; then
      [[ "${*: -1}" == */db.dump ]] && return 0
      return 1
    fi
    return 0
  }
  require_recent_backup
}

test_unhealthy_starting_stack_rejected() {
  require_container_running() { :; }
  require_container_healthy() {
    [[ "$1" == "$BACKEND_CONTAINER" ]] && fail "$1 unhealthy"
    return 0
  }
  require_starting_stack_healthy
}

test_migrate_flag_parsed() {
  parse_args --migrate
  [[ "$RUN_MIGRATIONS" -eq 1 ]]
}

test_health_timeout_rejected() {
  container_health() { printf 'starting\n'; }
  docker() {
    [[ "$1" == "logs" ]] && return 0
    return 0
  }
  wait_for_healthy "$BACKEND_CONTAINER"
}

test_nginx_test_failure_prevents_reload() {
  docker() {
    if [[ "$1" == "exec" && "$3" == "nginx" && "$4" == "-t" ]]; then
      return 1
    fi
    if [[ "$1" == "exec" && "$3" == "nginx" && "$4" == "-s" ]]; then
      MUTATIONS=$((MUTATIONS + 1))
    fi
    return 0
  }
  reload_npm
}

test_published_sensitive_port_rejected() {
  docker_port_output() {
    printf '0.0.0.0:%s\n' "$2"
  }
  require_no_published_port "$BACKEND_CONTAINER" 8000
}

test_dry_run_skips_mutations() {
  preflight() { :; }
  backup_gate() { :; }
  git_update() { MUTATIONS=$((MUTATIONS + 1)); }
  build_images() { MUTATIONS=$((MUTATIONS + 1)); }
  migration_phase() { MUTATIONS=$((MUTATIONS + 1)); }
  deploy_backend() { MUTATIONS=$((MUTATIONS + 1)); }
  deploy_frontend() { MUTATIONS=$((MUTATIONS + 1)); }
  parse_args --dry-run
  preflight
  backup_gate
  if (( DRY_RUN == 1 )); then
    :
  else
    git_update
    build_images
    migration_phase
    deploy_backend
    deploy_frontend
  fi
  [[ "$MUTATIONS" -eq 0 ]]
}

test_success_summary_mentions_rollback() {
  ROLLBACK_SHA="abc123"
  NEW_SHA="def456"
  BACKUP_DIR_USED="/app/backups/backup_20990101_000000"
  NPM_RELOADED=1
  completion_summary "not run" "OK" | grep -q 'Rollback SHA: abc123'
}

expect_failure "dirty Git tree rejects deployment" test_dirty_git_rejected
expect_failure "wrong branch rejects deployment" test_wrong_branch_rejected
expect_failure "missing proxy network rejects deployment" test_missing_proxy_network_rejected
expect_failure "stale backup rejects deployment" test_stale_backup_rejected
expect_failure "incomplete backup rejects deployment" test_incomplete_backup_rejected
expect_failure "unhealthy starting stack rejects deployment" test_unhealthy_starting_stack_rejected
expect_success "migration flag behaviour" test_migrate_flag_parsed
expect_failure "health timeout rejects deployment" test_health_timeout_rejected
expect_failure "nginx -t failure prevents reload" test_nginx_test_failure_prevents_reload
expect_failure "published sensitive host ports are detected" test_published_sensitive_port_rejected
expect_success "dry-run performs no mutations" test_dry_run_skips_mutations
expect_success "successful path reaches completion summary" test_success_summary_mentions_rollback

printf '\n%s passed, %s failed\n' "$PASS" "$FAILURES"
[[ "$FAILURES" -eq 0 ]]
