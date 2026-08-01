#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

mode="regular"
if [[ "${1:-}" == "--first-upgrade" ]]; then
  mode="first-upgrade"
elif [[ -n "${1:-}" && "${1:-}" != "--regular" ]]; then
  echo "Usage: $0 [--first-upgrade|--regular]" >&2
  exit 2
fi

test -f .env || { echo "Missing .env (copy .env.example and preserve existing values)." >&2; exit 1; }
python3 scripts/check_env_names.py .env \
  TZ POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD APP_DB_NAME APP_DB_USER APP_DB_PASSWORD

compose=(docker compose --env-file .env)
"${compose[@]}" config --quiet
compose_json="$("${compose[@]}" config --format json)"
python3 scripts/ci_assert_compose.py <<<"$compose_json"
python3 -c '
import json, sys
m=json.load(sys.stdin)
assert m.get("name") == "football-agent", "Compose project name must be football-agent"
volumes=m.get("volumes") or {}
postgres=volumes.get("postgres_data")
assert postgres is not None, "Required Compose volume postgres_data is missing"
assert postgres.get("name") == "football_postgres_data", \
    "Required Compose volume postgres_data must remain named football_postgres_data"
n8n=volumes.get("n8n_data")
if n8n is not None:
    assert n8n.get("name") == "football_n8n_data", \
        "Optional Compose volume n8n_data must remain named football_n8n_data"
env=m["services"]["migrate"]["environment"]
assert env["APP_DB_NAME"] == "football_intelligence"
assert env["APP_DB_USER"] == "football_app"
' <<<"$compose_json"

if [[ "${PREFLIGHT_SKIP_RUNTIME:-0}" == "1" ]]; then
  echo "Preflight configuration passed; runtime inspection was explicitly skipped."
  exit 0
fi

docker volume inspect football_postgres_data >/dev/null
if [[ "$mode" == "first-upgrade" ]]; then
  docker volume inspect football_n8n_data >/dev/null
else
  test -f .foundation-deployed || {
    echo "Missing .foundation-deployed. Use --first-upgrade for the legacy-to-Foundation transition." >&2
    exit 1
  }
  test -s .deployed-revision || {
    echo "Missing .deployed-revision; regular upgrade cannot establish a rollback target." >&2
    exit 1
  }
fi

validate_project_container() {
  local container="$1"
  if ! docker container inspect "$container" >/dev/null 2>&1; then
    return 0
  fi
  local project
  project="$(docker container inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$container")"
  test "$project" = "football-agent" || {
    echo "Refusing transition: $container belongs to Compose project '$project', not football-agent." >&2
    exit 1
  }
}

for container in football-postgres football-collector football-api football-worker \
  football-frontend football-proxy football-n8n football-adminer; do
  validate_project_container "$container"
done

test "$(docker container inspect --format '{{ range .Mounts }}{{ if eq .Destination "/var/lib/postgresql/data" }}{{ .Name }}{{ end }}{{ end }}' football-postgres)" = "football_postgres_data" || {
  echo "Refusing transition: football-postgres is not mounted from football_postgres_data." >&2
  exit 1
}

if docker container inspect football-n8n >/dev/null 2>&1; then
  test "$(docker container inspect --format '{{ range .Mounts }}{{ if eq .Destination "/home/node/.n8n" }}{{ .Name }}{{ end }}{{ end }}' football-n8n)" = "football_n8n_data" || {
    echo "Refusing transition: football-n8n is not mounted from football_n8n_data." >&2
    exit 1
  }
fi

echo "Preflight passed for $mode: project identity and persistent volumes are verified."
