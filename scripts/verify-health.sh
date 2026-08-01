#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

compose=(docker compose --env-file .env)
compose_json="$("${compose[@]}" config --format json)"
read -r bind_address proxy_port < <(python3 -c '
import json,sys
p=json.load(sys.stdin)["services"]["proxy"]["ports"][0]
print(p.get("host_ip") or "127.0.0.1", p["published"])
' <<<"$compose_json")
app_db_user="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["migrate"]["environment"]["APP_DB_USER"])' <<<"$compose_json")"

url="http://${bind_address}:${proxy_port}"
deadline=$((SECONDS + 120))
until curl --fail --silent "$url/health" >/dev/null 2>&1 \
  && "${compose[@]}" exec -T postgres psql -U "$app_db_user" -d football_intelligence -tAc \
    "SELECT CASE WHEN EXISTS (SELECT 1 FROM core.schema_migrations WHERE version = '008_add_job_queue') THEN 'ok' ELSE 'missing' END" \
    | tr -d '[:space:]' | grep -qx ok; do
  if (( SECONDS >= deadline )); then
    echo "Health verification timed out for proxy/API or migration 008." >&2
    "${compose[@]}" ps -a >&2
    exit 1
  fi
  sleep 5
done
echo "Proxy, API, and football_intelligence migration health verified."
