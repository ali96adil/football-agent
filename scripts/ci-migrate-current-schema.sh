#!/usr/bin/env bash
set -euo pipefail
# This database is created solely by GitHub Actions. It is never a Pi backup.
cd "$(dirname "$0")/.."
fixture_db="${APP_DB_NAME}"
test "$fixture_db" = "football_intelligence" || {
  echo "Current-schema fixture must target only the ephemeral football_intelligence CI database." >&2
  exit 1
}
export PGPASSWORD="$APP_DB_PASSWORD"
psql -h "$APP_DB_HOST" -p "$APP_DB_PORT" -U "$APP_DB_USER" -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS ${fixture_db} WITH (FORCE)"
psql -h "$APP_DB_HOST" -p "$APP_DB_PORT" -U "$APP_DB_USER" -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${fixture_db}"
# Recreate the checked-in schema as it stood immediately before migration 008.
# The fixture is derived from source, not from any Pi dump or production data.
sed '/-- v1 foundation: durable background job queue/,$d' database/schema.sql \
  | psql -h "$APP_DB_HOST" -p "$APP_DB_PORT" -U "$APP_DB_USER" -d "$fixture_db" -v ON_ERROR_STOP=1
python services/collector/scripts/migrate.py --migrations-root "$PWD"
psql -h "$APP_DB_HOST" -p "$APP_DB_PORT" -U "$APP_DB_USER" -d "$fixture_db" -tAc "SELECT to_regclass('core.jobs')" | grep -qx core.jobs
psql -h "$APP_DB_HOST" -p "$APP_DB_PORT" -U "$APP_DB_USER" -d "$fixture_db" -tAc "SELECT to_regclass('core.worker_heartbeats')" | grep -qx core.worker_heartbeats
