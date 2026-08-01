#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
root="$PWD"

test_root="$(mktemp -d)"
cleanup() { rm -rf -- "$test_root"; }
trap cleanup EXIT

create_docker_stub() {
  local target="$1"
  mkdir -p "$target"
  cat > "$target/docker" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "compose" ]]; then
  shift
  arguments=" $* "
  if [[ "$arguments" == *" config "* && "$arguments" == *" --format json "* ]]; then
    cat <<'JSON'
{"name":"football-agent","services":{"proxy":{"ports":[{"host_ip":"127.0.0.1","published":18088}],"networks":{"football_edge":{},"football_ingress":{}}},"postgres":{"networks":{"football_private":{}},"healthcheck":{"test":["CMD","true"]}},"migrate":{"environment":{"APP_DB_NAME":"football_intelligence","APP_DB_USER":"football_app"}},"api":{"networks":{"football_edge":{},"football_private":{},"football_egress":{}},"healthcheck":{"test":["CMD","true"]}},"worker":{"command":["python","-m","scripts.worker"],"networks":{"football_private":{},"football_egress":{}}},"frontend":{"networks":{"football_edge":{},"football_egress":{}},"healthcheck":{"test":["CMD","true"]}}},"volumes":{"postgres_data":{"name":"football_postgres_data"}},"networks":{"football_ingress":{},"football_edge":{"internal":true},"football_private":{"internal":true},"football_egress":{}}}
JSON
    exit 0
  fi
  if [[ "$arguments" == *" config "* ]]; then
    exit 0
  fi
  if [[ "$arguments" == *" ps "* && "$arguments" == *" -q "* ]]; then
    service="${@: -1}"
    [[ "${TEST_SCENARIO:-}" == "missing_proxy" && "$service" == "proxy" ]] || printf 'container-%s\n' "$service"
    exit 0
  fi
  if [[ "$arguments" == *" exec "* && "$arguments" == *" pg_dump "* ]]; then
    echo "test backup"
    exit 0
  fi
  if [[ "$arguments" == *" exec "* && "$arguments" == *" psql "* ]]; then
    echo "ok"
    exit 0
  fi
  case "$arguments" in
    *" pull "*|*" build "*|*" up "*|*" run "*) exit 0 ;;
  esac
fi

if [[ "${1:-}" == "container" && "${2:-}" == "inspect" ]]; then
  container_id="${@: -1}"
  service="${container_id#container-}"
  state="running"
  health="none"
  restart_count="0"
  case "$service" in
    postgres|api|frontend) health="healthy" ;;
  esac
  if [[ "${TEST_SCENARIO:-}" == "frontend_failed" && "$service" == "frontend" ]]; then
    state="exited"
    health="unhealthy"
  elif [[ "${TEST_SCENARIO:-}" == "api_dead" && "$service" == "api" ]]; then
    state="dead"
  elif [[ "${TEST_SCENARIO:-}" == "frontend_unhealthy" && "$service" == "frontend" ]]; then
    health="unhealthy"
  elif [[ "${TEST_SCENARIO:-}" == "worker_restarting" && "$service" == "worker" ]]; then
    state="restarting"
    restart_count="4"
  elif [[ "${TEST_SCENARIO:-}" == "worker_restart_count_changed" && "$service" == "worker" ]]; then
    restart_count="$(<"$WORKER_COUNT_FILE")"
    printf '%s\n' "$((restart_count + 1))" > "$WORKER_COUNT_FILE"
  fi
  printf '%s|%s|%s\n' "$state" "$health" "$restart_count"
  exit 0
fi

echo "Unexpected docker stub invocation: $*" >&2
exit 90
STUB
  chmod +x "$target/docker"
}

create_curl_stub() {
  local target="$1"
  cat > "$target/curl" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
url="${@: -1}"
printf '%s\n' "$url" >> "$CURL_LOG"
if [[ "${TEST_SCENARIO:-}" == "proxy_frontend_unreachable" && "$url" == */ ]]; then
  exit 22
fi
exit 0
STUB
  chmod +x "$target/curl"
}

prepare_fixture() {
  local case_name="$1"
  local case_root="$test_root/$case_name"
  local repo="$case_root/repo"
  mkdir -p "$repo"
  cp -R scripts "$repo/scripts"
  cp compose.yaml .env.ci "$repo/"
  cp "$repo/.env.ci" "$repo/.env"
  (
    cd "$repo"
    git init -q
    git config user.name "Health Scenario Test"
    git config user.email "health-scenario@example.invalid"
    git add scripts compose.yaml .env.ci
    git commit -qm "fixture: previous release"
    git rev-parse HEAD > .deployed-revision
    cp .deployed-revision .last-known-good-revision
    touch .foundation-deployed
    echo "target" > release-marker
    git add release-marker
    git commit -qm "fixture: target release"
  )
  mkdir -p "$case_root/bin"
  create_docker_stub "$case_root/bin"
  create_curl_stub "$case_root/bin"
  cat > "$repo/scripts/rollback.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'invoked\n' > "$ROLLBACK_MARKER"
STUB
  chmod +x "$repo/scripts/rollback.sh"
  printf '%s\n' "$repo"
}

run_case() {
  local scenario="$1" expected="$2"
  local repo case_root previous_revision target_revision status
  repo="$(prepare_fixture "$scenario")"
  case_root="$(dirname "$repo")"
  previous_revision="$(<"$repo/.deployed-revision")"
  target_revision="$(git -C "$repo" rev-parse HEAD)"
  : > "$case_root/curl.log"
  printf '0\n' > "$case_root/worker-count"

  set +e
  (
    cd "$repo"
    PATH="$case_root/bin:$PATH" \
      TEST_SCENARIO="$scenario" \
      CURL_LOG="$case_root/curl.log" \
      WORKER_COUNT_FILE="$case_root/worker-count" \
      ROLLBACK_MARKER="$case_root/rollback.marker" \
      BACKUP_DIR="$case_root/backups" \
      PREFLIGHT_SKIP_RUNTIME=1 \
      VERIFY_HEALTH_TIMEOUT_SECONDS=0 \
      VERIFY_HEALTH_RETRY_SECONDS=0 \
      VERIFY_HEALTH_STABILITY_SECONDS=0 \
      ./scripts/deploy.sh >"$case_root/output.log" 2>&1
  )
  status=$?
  set -e

  if [[ "$expected" == "failure" ]]; then
    [[ "$status" -ne 0 ]] || { echo "$scenario unexpectedly succeeded" >&2; return 1; }
    [[ -f "$case_root/rollback.marker" ]] || { echo "$scenario did not invoke rollback" >&2; return 1; }
    [[ "$(<"$repo/.deployed-revision")" == "$previous_revision" ]] || {
      echo "$scenario changed deployed revision before successful health" >&2
      return 1
    }
    [[ "$(<"$repo/.last-known-good-revision")" == "$previous_revision" ]] || {
      echo "$scenario did not preserve the previous last-known-good revision" >&2
      return 1
    }
  else
    [[ "$status" -eq 0 ]] || { cat "$case_root/output.log" >&2; return 1; }
    [[ ! -f "$case_root/rollback.marker" ]] || { echo "$scenario invoked rollback" >&2; return 1; }
    [[ "$(<"$repo/.deployed-revision")" == "$target_revision" ]] || {
      echo "$scenario did not record the healthy target revision" >&2
      return 1
    }
    [[ "$(<"$repo/.last-known-good-revision")" == "$previous_revision" ]] || {
      echo "$scenario did not retain the rollback revision" >&2
      return 1
    }
    grep -qx 'http://127.0.0.1:18088/' "$case_root/curl.log"
    grep -qx 'http://127.0.0.1:18088/health' "$case_root/curl.log"
  fi
}

run_case frontend_failed failure
run_case worker_restarting failure
run_case proxy_frontend_unreachable failure
run_case all_healthy success
run_case api_dead failure
run_case frontend_unhealthy failure
run_case missing_proxy failure
run_case worker_restart_count_changed failure

echo "Deploy health and automatic rollback scenarios passed."
