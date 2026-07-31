#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/preflight.sh
set -a; . ./.env; set +a
backup_dir="${BACKUP_DIR:-./backups}"
mkdir -p "$backup_dir"
stamp="$(date +%Y%m%d-%H%M%S)"
echo "Creating explicit backup of football_intelligence (never \$POSTGRES_DB)…"
docker compose exec -T postgres pg_dump -U "$APP_DB_USER" -d football_intelligence -Fc > "$backup_dir/football_intelligence-$stamp.dump"
echo "Applying checksum-protected migrations, then replacing application containers only."
docker compose run --rm migrate
docker compose up -d --no-deps api worker frontend proxy
./scripts/verify-health.sh
echo "Deployment complete. Do NOT run: docker compose down -v"
