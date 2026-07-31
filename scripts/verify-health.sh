#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
url="http://${PROXY_BIND_ADDRESS:-127.0.0.1}:${PROXY_HTTP_PORT:-8088}"
curl --fail --silent --show-error "$url/health" >/dev/null
docker compose exec -T postgres psql -U "$APP_DB_USER" -d football_intelligence -tAc \
  "SELECT CASE WHEN EXISTS (SELECT 1 FROM core.schema_migrations WHERE version = '008_add_job_queue') THEN 'ok' ELSE 'missing' END" \
  | grep -qx ok
echo "Proxy, API, and football_intelligence migration health verified."
