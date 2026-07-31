#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Preflight: no command in this repository should use 'docker compose down -v'."
test -f .env || { echo "Missing .env (copy .env.example and fill existing values)." >&2; exit 1; }
set -a; . ./.env; set +a
test "${APP_DB_NAME:-}" = "football_intelligence" || { echo "APP_DB_NAME must be football_intelligence." >&2; exit 1; }
test "${APP_DB_USER:-}" = "football_app" || { echo "APP_DB_USER must be football_app." >&2; exit 1; }
test -n "${APP_DB_PASSWORD:-}" || { echo "APP_DB_PASSWORD is required." >&2; exit 1; }
docker compose config --quiet
docker volume inspect football_postgres_data >/dev/null
echo "Preflight passed. Existing PostgreSQL volume football_postgres_data was found and will not be recreated."
