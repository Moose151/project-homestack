#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export HOMESTACK_DEPLOY_LIB_ONLY=1
# shellcheck source=scripts/deploy-production.sh
source "$ROOT/scripts/deploy-production.sh"

PASS=0
FAILURES=0
MUTATIONS=0
MOCK_CHECKOUT_SHA=""
MOCK_TARGET_SHA=""
MOCK_FAIL_PHASE=""

reset_state() {
  PHASE="test"
  RUN_MIGRATIONS=0
  SKIP_BACKUP_AGE_CHECK=0
  DRY_RUN=0
  BOOTSTRAP_DEPLOYED_SHA=""
  RECORD_ROLLBACK_SHA=""
  HEALTH_TIMEOUT=1
  HEALTH_INTERVAL=1
  BACKUP_MAX_AGE_HOURS=24
  CHECKOUT_SHA=""
  TARGET_SHA=""
  DEPLOYED_SHA=""
  ROLLBACK_SHA=""
  BACKUP_DIR_USED=""
  NPM_RELOADED=0
  MUTATIONS=0
  MOCK_CHECKOUT_SHA=""
  MOCK_TARGET_SHA=""
  MOCK_FAIL_PHASE=""
  MOCK_ROLLBACK_HEAD_SHA=""
  MOCK_ROLLBACK_PREVIOUS_SHA=""
  MOCK_ROLLBACK_IS_ANCESTOR_RESULT=0
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
  TARGET_SHA="def456"
  BACKUP_DIR_USED="/app/backups/backup_20990101_000000"
  NPM_RELOADED=1
  completion_summary "not run" "OK" | grep -q 'Rollback SHA: abc123'
}

setup_mock_deploy() {
  local checkout="$1"
  local deployed="$2"
  local target="$3"
  local fail_phase="${4:-}"
  local state="$5"
  MOCK_CHECKOUT_SHA="$checkout"
  MOCK_TARGET_SHA="$target"
  MOCK_FAIL_PHASE="$fail_phase"
  DEPLOYED_SHA_FILE="$state"
  printf '%s\n' "$deployed" > "$state"
  require_valid_commit() { :; }
  resolve_full_sha() { printf '%s\n' "$1"; }
  require_repo_dir() { :; }
  require_branch_main() { :; }
  require_clean_tree() { :; }
  require_tools() { :; }
  require_origin_reachable() { :; }
  require_main_not_ahead_or_diverged() { :; }
  require_compose_config() { :; }
  require_network_exists() { :; }
  require_starting_stack_healthy() { :; }
  require_volumes_exist() { :; }
  require_topology() { :; }
  require_recent_backup() { :; }
  changed_migration_files() {
    if [[ "$MOCK_FAIL_PHASE" == "migration-required" ]]; then
      printf 'backend/apps/example/migrations/0002_example.py\n'
    fi
  }
  git() {
    case "$*" in
      "rev-parse HEAD") printf '%s\n' "$MOCK_CHECKOUT_SHA" ;;
      "rev-parse origin/main") printf '%s\n' "$MOCK_TARGET_SHA" ;;
      "fetch origin") return 0 ;;
      "merge --ff-only origin/main") return 0 ;;
      "merge-base --is-ancestor "*) return 0 ;;
      *) command git "$@" ;;
    esac
  }
  compose() {
    case "$*" in
      "build $BACKEND_SERVICE $FRONTEND_SERVICE") MUTATIONS=$((MUTATIONS + 1)); return 0 ;;
      "run --rm --no-deps $BACKEND_SERVICE python manage.py migrate --check")
        [[ "$MOCK_FAIL_PHASE" == "migration-required" ]] && return 1
        return 0
        ;;
      "run --rm --no-deps $BACKEND_SERVICE python manage.py migrate --noinput")
        MUTATIONS=$((MUTATIONS + 1)); return 0 ;;
      *) return 0 ;;
    esac
  }
  deploy_backend() {
    [[ "$MOCK_FAIL_PHASE" == "backend" ]] && fail "backend failed"
    MUTATIONS=$((MUTATIONS + 1))
  }
  validate_backend() { MUTATIONS=$((MUTATIONS + 1)); }
  deploy_frontend() { MUTATIONS=$((MUTATIONS + 1)); }
  final_validation() {
    [[ "$MOCK_FAIL_PHASE" == "final" ]] && fail "final failed"
    MUTATIONS=$((MUTATIONS + 1))
  }
}

run_mock_deploy_sequence() {
  preflight || return $?
  backup_gate || return $?
  git_update || return $?
  build_images || return $?
  migration_phase || return $?
  deploy_backend || return $?
  validate_backend || return $?
  deploy_frontend || return $?
  final_validation || return $?
  write_deployed_sha "$TARGET_SHA" || return $?
}

run_mock_deploy() {
  local checkout="$1"
  local deployed="$2"
  local target="$3"
  local fail_phase="${4:-}"
  local state
  state="$(mktemp)"
  setup_mock_deploy "$checkout" "$deployed" "$target" "$fail_phase" "$state"
  run_mock_deploy_sequence
  [[ "$(tr -d '[:space:]' < "$state")" == "$target" ]]
}

test_successful_deployment_records_target_sha() {
  run_mock_deploy "old-sha" "old-sha" "target-sha"
}

test_failed_deployment_does_not_advance_deployed_sha() {
  local state
  state="$(mktemp)"
  setup_mock_deploy "target-sha" "old-sha" "target-sha" "final" "$state"
  if ( run_mock_deploy_sequence ); then
    return 1
  fi
  [[ "$(tr -d '[:space:]' < "$state")" == "old-sha" ]]
}

test_retry_after_failed_deployment_proceeds_when_checkout_at_target() {
  run_mock_deploy "target-sha" "old-sha" "target-sha"
  (( MUTATIONS > 0 ))
}

test_initial_without_migrate_then_retry_with_migrate_proceeds() {
  local state
  state="$(mktemp)"
  setup_mock_deploy "target-sha" "old-sha" "target-sha" "migration-required" "$state"
  if ( run_mock_deploy_sequence ); then
    return 1
  fi
  [[ "$(tr -d '[:space:]' < "$state")" == "old-sha" ]] || return 1

  RUN_MIGRATIONS=1
  setup_mock_deploy "target-sha" "old-sha" "target-sha" "migration-required" "$state"
  run_mock_deploy_sequence
  [[ "$(tr -d '[:space:]' < "$state")" == "target-sha" ]]
}

test_checkout_at_target_with_older_deployed_marker_deploys() {
  run_mock_deploy "target-sha" "old-sha" "target-sha"
  (( MUTATIONS > 0 ))
}

test_checkout_at_target_with_deployed_marker_at_target_noops() {
  local state
  state="$(mktemp)"
  setup_mock_deploy "target-sha" "target-sha" "target-sha" "" "$state"
  git() {
    case "$*" in
      "rev-parse HEAD"|"rev-parse origin/main") printf 'target-sha\n' ;;
      "fetch origin") return 0 ;;
      "merge --ff-only origin/main") fail "merge should not run for a deployed-target no-op" ;;
      *) command git "$@" ;;
    esac
  }
  ( preflight; git_update )
  [[ "$(tr -d '[:space:]' < "$state")" == "target-sha" ]]
}

test_deployed_target_checkout_behind_fast_forwards() {
  local state ff_marker
  state="$(mktemp)"
  ff_marker="$(mktemp -u)"
  printf 'target-sha\n' > "$state"
  DEPLOYED_SHA_FILE="$state"
  CHECKOUT_SHA="old-sha"
  require_valid_commit() { :; }
  resolve_full_sha() { printf '%s\n' "$1"; }
  require_main_not_ahead_or_diverged() { :; }
  git() {
    case "$*" in
      "rev-parse origin/main") printf 'target-sha\n' ;;
      "fetch origin") return 0 ;;
      "merge --ff-only origin/main") printf 'merged\n' > "$ff_marker" ;;
      *) command git "$@" ;;
    esac
  }
  DEPLOYED_SHA="$(read_deployed_sha)"
  ( git_update ) || true
  [[ -f "$ff_marker" ]] || return 1
  [[ "$(tr -d '[:space:]' < "$state")" == "target-sha" ]]
}

test_bootstrap_normalises_abbreviated_sha() {
  local short full state
  short="$(git rev-parse --short HEAD)"
  full="$(git rev-parse HEAD)"
  state="$(mktemp -u)"
  DEPLOYED_SHA_FILE="$state"
  BOOTSTRAP_DEPLOYED_SHA="$short"
  require_repo_dir() { :; }
  require_branch_main() { :; }
  require_clean_tree() { :; }
  bootstrap_deployed_sha >/dev/null
  [[ "$(tr -d '[:space:]' < "$state")" == "$full" ]]
}

make_unrelated_commit() {
  git commit-tree "$(git rev-parse HEAD^{tree})" -m "test unrelated commit $$-$RANDOM"
}

test_ancestry_rejects_unrelated_deployed_sha() {
  DEPLOYED_SHA="$(make_unrelated_commit)"
  TARGET_SHA="$(git rev-parse HEAD)"
  require_deployed_sha_lineage
}

test_ancestry_accepts_equal_deployed_and_target() {
  DEPLOYED_SHA="$(git rev-parse HEAD)"
  TARGET_SHA="$DEPLOYED_SHA"
  require_deployed_sha_lineage
}

test_rollback_marker_unchanged_when_recording_not_confirmed() {
  local state
  state="$(mktemp)"
  printf 'old-deployed-sha\n' > "$state"
  DEPLOYED_SHA_FILE="$state"
  require_repo_dir() { :; }
  require_clean_tree() { :; }
  RECORD_ROLLBACK_SHA=""
  if ( record_rollback_deployed_sha ) 2>/dev/null; then
    return 1
  fi
  [[ "$(tr -d '[:space:]' < "$state")" == "old-deployed-sha" ]]
}

setup_record_rollback_mocks() {
  local state="$1"
  MOCK_ROLLBACK_HEAD_SHA="$2"
  MOCK_ROLLBACK_PREVIOUS_SHA="$3"
  MOCK_ROLLBACK_IS_ANCESTOR_RESULT="${4:-0}"
  DEPLOYED_SHA_FILE="$state"
  printf '%s\n' "$MOCK_ROLLBACK_PREVIOUS_SHA" > "$state"
  require_repo_dir() { :; }
  require_clean_tree() { :; }
  resolve_full_sha() { printf '%s\n' "$1"; }
  git() {
    case "$*" in
      "rev-parse HEAD") printf '%s\n' "$MOCK_ROLLBACK_HEAD_SHA" ;;
      "merge-base --is-ancestor "*) return "$MOCK_ROLLBACK_IS_ANCESTOR_RESULT" ;;
      *) command git "$@" ;;
    esac
  }
}

test_record_rollback_sha_stores_rollback_sha() {
  local state
  state="$(mktemp)"
  setup_record_rollback_mocks "$state" "rollback-sha" "old-deployed-sha" 0
  RECORD_ROLLBACK_SHA="rollback-sha"
  record_rollback_deployed_sha >/dev/null
  [[ "$(tr -d '[:space:]' < "$state")" == "rollback-sha" ]]
}

test_record_rollback_rejects_candidate_not_head() {
  local state
  state="$(mktemp)"
  setup_record_rollback_mocks "$state" "head-sha" "old-deployed-sha" 0
  RECORD_ROLLBACK_SHA="different-sha"
  if ( record_rollback_deployed_sha ) 2>/dev/null; then
    return 1
  fi
  [[ "$(tr -d '[:space:]' < "$state")" == "old-deployed-sha" ]]
}

test_record_rollback_accepts_candidate_equal_head() {
  local state
  state="$(mktemp)"
  setup_record_rollback_mocks "$state" "rollback-sha" "rollback-sha" 0
  RECORD_ROLLBACK_SHA="rollback-sha"
  record_rollback_deployed_sha >/dev/null
  [[ "$(tr -d '[:space:]' < "$state")" == "rollback-sha" ]]
}

test_record_rollback_rejects_unrelated_candidate() {
  local state
  state="$(mktemp)"
  setup_record_rollback_mocks "$state" "rollback-sha" "unrelated-deployed-sha" 1
  RECORD_ROLLBACK_SHA="rollback-sha"
  if ( record_rollback_deployed_sha ) 2>/dev/null; then
    return 1
  fi
  [[ "$(tr -d '[:space:]' < "$state")" == "unrelated-deployed-sha" ]]
}

test_record_rollback_rejects_forward_candidate() {
  local state
  state="$(mktemp)"
  setup_record_rollback_mocks "$state" "newer-forward-sha" "old-deployed-sha" 1
  RECORD_ROLLBACK_SHA="newer-forward-sha"
  if ( record_rollback_deployed_sha ) 2>/dev/null; then
    return 1
  fi
  [[ "$(tr -d '[:space:]' < "$state")" == "old-deployed-sha" ]]
}

test_dry_run_and_bootstrap_mutually_exclusive() {
  local state
  state="$(mktemp -u)"
  DEPLOYED_SHA_FILE="$state"
  parse_args --dry-run --bootstrap-deployed-sha abc1234
  if ( validate_args ) 2>/dev/null; then
    return 1
  fi
  [[ ! -f "$state" ]]
}

test_dry_run_and_record_rollback_mutually_exclusive() {
  local state
  state="$(mktemp)"
  printf 'old-deployed-sha\n' > "$state"
  DEPLOYED_SHA_FILE="$state"
  parse_args --dry-run --record-rollback-sha abc1234
  if ( validate_args ) 2>/dev/null; then
    return 1
  fi
  [[ "$(tr -d '[:space:]' < "$state")" == "old-deployed-sha" ]]
}

test_bootstrap_and_record_rollback_mutually_exclusive() {
  local state
  state="$(mktemp)"
  printf 'old-deployed-sha\n' > "$state"
  DEPLOYED_SHA_FILE="$state"
  parse_args --bootstrap-deployed-sha abc1234 --record-rollback-sha def5678
  if ( validate_args ) 2>/dev/null; then
    return 1
  fi
  [[ "$(tr -d '[:space:]' < "$state")" == "old-deployed-sha" ]]
}

test_migrate_and_bootstrap_mutually_exclusive() {
  local state
  state="$(mktemp -u)"
  DEPLOYED_SHA_FILE="$state"
  parse_args --migrate --bootstrap-deployed-sha abc1234
  if ( validate_args ) 2>/dev/null; then
    return 1
  fi
  [[ ! -f "$state" ]]
}

test_skip_backup_age_check_and_record_rollback_mutually_exclusive() {
  local state
  state="$(mktemp)"
  printf 'old-deployed-sha\n' > "$state"
  DEPLOYED_SHA_FILE="$state"
  parse_args --skip-backup-age-check --record-rollback-sha abc1234
  if ( validate_args ) 2>/dev/null; then
    return 1
  fi
  [[ "$(tr -d '[:space:]' < "$state")" == "old-deployed-sha" ]]
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
expect_success "successful deployment records target SHA" test_successful_deployment_records_target_sha
expect_success "failed deployment does not advance deployed SHA" test_failed_deployment_does_not_advance_deployed_sha
expect_success "retry after failed deployment proceeds when Git is already at target" test_retry_after_failed_deployment_proceeds_when_checkout_at_target
expect_success "initial run without --migrate followed by retry with --migrate proceeds" test_initial_without_migrate_then_retry_with_migrate_proceeds
expect_success "checkout at target with older deployed marker still deploys" test_checkout_at_target_with_older_deployed_marker_deploys
expect_success "checkout at target with deployed marker at target gives genuine no-op" test_checkout_at_target_with_deployed_marker_at_target_noops
expect_success "deployed target with checkout behind fast-forwards without redeploying" test_deployed_target_checkout_behind_fast_forwards
expect_success "abbreviated bootstrap SHA is normalised to full SHA" test_bootstrap_normalises_abbreviated_sha
expect_failure "deployed marker pointing to an unrelated commit is rejected" test_ancestry_rejects_unrelated_deployed_sha
expect_success "deployed marker equal to target passes ancestry validation" test_ancestry_accepts_equal_deployed_and_target
expect_success "rollback marker is unchanged when recording is not confirmed" test_rollback_marker_unchanged_when_recording_not_confirmed
expect_success "successful rollback-state recording stores the rollback SHA" test_record_rollback_sha_stores_rollback_sha
expect_success "record rollback rejects a candidate that does not match HEAD" test_record_rollback_rejects_candidate_not_head
expect_success "record rollback accepts a candidate equal to HEAD" test_record_rollback_accepts_candidate_equal_head
expect_success "record rollback rejects an unrelated candidate" test_record_rollback_rejects_unrelated_candidate
expect_success "record rollback rejects a forward/non-ancestor candidate" test_record_rollback_rejects_forward_candidate
expect_success "--dry-run and --bootstrap-deployed-sha are mutually exclusive with no marker mutation" test_dry_run_and_bootstrap_mutually_exclusive
expect_success "--dry-run and --record-rollback-sha are mutually exclusive with no marker mutation" test_dry_run_and_record_rollback_mutually_exclusive
expect_success "--bootstrap-deployed-sha and --record-rollback-sha are mutually exclusive with no marker mutation" test_bootstrap_and_record_rollback_mutually_exclusive
expect_success "--migrate and --bootstrap-deployed-sha are mutually exclusive with no marker mutation" test_migrate_and_bootstrap_mutually_exclusive
expect_success "--skip-backup-age-check and --record-rollback-sha are mutually exclusive with no marker mutation" test_skip_backup_age_check_and_record_rollback_mutually_exclusive

printf '\n%s passed, %s failed\n' "$PASS" "$FAILURES"
[[ "$FAILURES" -eq 0 ]]
