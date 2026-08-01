#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

compose=(docker compose --env-file .env)
compose_json="$("${compose[@]}" config --format json)"

IFS=$'\t' read -r proxy_url app_db_user app_db_name < <(python3 -c '
import json
import sys

model = json.load(sys.stdin)
port = model["services"]["proxy"]["ports"][0]
host = port.get("host_ip") or "127.0.0.1"
if host in {"0.0.0.0", "::"}:
    host = "127.0.0.1"
elif ":" in host and not host.startswith("["):
    host = f"[{host}]"
environment = model["services"]["migrate"]["environment"]
published = port["published"]
print(
    f"http://{host}:{published}",
    environment["APP_DB_USER"],
    environment["APP_DB_NAME"],
    sep="\t",
)
' <<<"$compose_json")

declare -A requires_health=()
while read -r service; do
  [[ -n "$service" ]] && requires_health["$service"]=1
done < <(python3 -c '
import json
import sys

for name, service in json.load(sys.stdin)["services"].items():
    if service.get("healthcheck") and not service["healthcheck"].get("disable", False):
        print(name)
' <<<"$compose_json")

required_services=(postgres api worker frontend proxy)
timeout_seconds="${VERIFY_HEALTH_TIMEOUT_SECONDS:-120}"
retry_seconds="${VERIFY_HEALTH_RETRY_SECONDS:-5}"
stability_seconds="${VERIFY_HEALTH_STABILITY_SECONDS:-5}"
curl_timeout_seconds="${VERIFY_HEALTH_CURL_TIMEOUT_SECONDS:-10}"
for value in "$timeout_seconds" "$retry_seconds" "$stability_seconds" "$curl_timeout_seconds"; do
  [[ "$value" =~ ^[0-9]+$ ]] || {
    echo "Health verification timing values must be non-negative integers." >&2
    exit 2
  }
done

failure_reason=""
worker_restart_count=""

inspect_required_services() {
  local service container_output container_id inspect_output state health restart_count
  local -a container_ids

  for service in "${required_services[@]}"; do
    if ! container_output="$("${compose[@]}" ps --all -q "$service" 2>/dev/null)"; then
      failure_reason="$service container lookup failed"
      return 1
    fi
    if [[ -z "$container_output" ]]; then
      failure_reason="$service container is missing"
      return 1
    fi
    mapfile -t container_ids <<<"$container_output"
    if [[ "${#container_ids[@]}" -ne 1 || -z "${container_ids[0]}" ]]; then
      failure_reason="$service must resolve to exactly one container"
      return 1
    fi
    container_id="${container_ids[0]}"
    if ! inspect_output="$(docker container inspect --format \
      '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}|{{.RestartCount}}' \
      "$container_id" 2>/dev/null)"; then
      failure_reason="$service container inspection failed"
      return 1
    fi
    IFS='|' read -r state health restart_count <<<"$inspect_output"
    if [[ "$state" != "running" ]]; then
      failure_reason="$service container state is ${state:-unknown}"
      return 1
    fi
    if [[ "$health" == "unhealthy" ]]; then
      failure_reason="$service container is unhealthy"
      return 1
    fi
    if [[ -n "${requires_health[$service]:-}" && "$health" != "healthy" ]]; then
      failure_reason="$service healthcheck state is ${health:-missing}"
      return 1
    fi
    if [[ "$service" == "worker" ]]; then
      [[ "$restart_count" =~ ^[0-9]+$ ]] || {
        failure_reason="worker restart count is unavailable"
        return 1
      }
      worker_restart_count="$restart_count"
    fi
  done
}

check_proxy_routes() {
  if ! curl --fail --silent --show-error --max-time "$curl_timeout_seconds" \
    "$proxy_url/" >/dev/null 2>&1; then
    failure_reason="proxy cannot serve the frontend page"
    return 1
  fi
  if ! curl --fail --silent --show-error --max-time "$curl_timeout_seconds" \
    "$proxy_url/health" >/dev/null 2>&1; then
    failure_reason="proxy cannot serve the API health endpoint"
    return 1
  fi
}

check_migration() {
  local migration_status
  if ! migration_status="$("${compose[@]}" exec -T postgres \
    psql -v ON_ERROR_STOP=1 -U "$app_db_user" -d "$app_db_name" -tAc \
      "SELECT CASE WHEN EXISTS (SELECT 1 FROM core.schema_migrations WHERE version = '013_add_telegram_destinations') THEN 'ok' ELSE 'missing' END" \
    2>/dev/null)"; then
    failure_reason="migration verification query failed"
    return 1
  fi
  if ! tr -d '[:space:]' <<<"$migration_status" | grep -qx ok; then
    failure_reason="migration 013_add_telegram_destinations is missing"
    return 1
  fi
}

check_release() {
  inspect_required_services && check_proxy_routes && check_migration
}

deadline=$((SECONDS + timeout_seconds))
while true; do
  if check_release; then
    initial_worker_restart_count="$worker_restart_count"
    (( stability_seconds == 0 )) || sleep "$stability_seconds"
    if check_release; then
      if [[ "$worker_restart_count" == "$initial_worker_restart_count" ]]; then
        echo "Postgres, API, worker, frontend, proxy, proxy routes, and migration health verified."
        exit 0
      fi
      failure_reason="worker restarted during the health stability window"
    fi
  fi

  if (( SECONDS >= deadline )); then
    echo "Health verification failed: ${failure_reason:-unknown failure}." >&2
    "${compose[@]}" ps -a >&2 || true
    exit 1
  fi
  sleep "$retry_seconds"
done
