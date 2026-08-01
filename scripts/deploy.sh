#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

mode="regular"
dry_run=0
for argument in "$@"; do
  case "$argument" in
    --first-upgrade) mode="first-upgrade" ;;
    --dry-run) dry_run=1 ;;
    *) echo "Usage: $0 [--first-upgrade] [--dry-run]" >&2; exit 2 ;;
  esac
done

preflight_mode="--regular"
[[ "$mode" == "first-upgrade" ]] && preflight_mode="--first-upgrade"
./scripts/preflight.sh "$preflight_mode"

target_revision="$(git rev-parse --verify HEAD^{commit})"
if [[ "$mode" == "first-upgrade" ]]; then
  test -s .last-known-good-revision || {
    echo "First upgrade requires .last-known-good-revision recorded before checkout." >&2
    exit 1
  }
  git cat-file -e "$(<.last-known-good-revision)^{commit}"
elif [[ -s .deployed-revision ]]; then
  git cat-file -e "$(<.deployed-revision)^{commit}"
fi

if [[ "$dry_run" == "1" ]]; then
  echo "DRY RUN: preflight passed; no containers were stopped or changed."
  echo "Planned order: pull -> build -> backup -> migrate -> validated legacy cleanup -> up --remove-orphans -> health."
  exit 0
fi

if [[ "$mode" == "regular" ]]; then
  cp .deployed-revision .last-known-good-revision
fi

compose=(docker compose --env-file .env)
echo "Pulling pinned runtime images before changing containers."
"${compose[@]}" pull postgres proxy
echo "Building every local production service before changing containers."
"${compose[@]}" build --pull api worker migrate frontend

compose_json="$("${compose[@]}" config --format json)"
app_db_user="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["migrate"]["environment"]["APP_DB_USER"])' <<<"$compose_json")"
backup_dir="${BACKUP_DIR:-./backups}"
mkdir -p "$backup_dir"
stamp="$(date +%Y%m%d-%H%M%S)"
echo "Creating an explicit football_intelligence backup."
"${compose[@]}" exec -T postgres pg_dump -U "$app_db_user" -d football_intelligence -Fc \
  > "$backup_dir/football_intelligence-$stamp.dump"

echo "Applying atomic checksum-protected migrations."
"${compose[@]}" up -d --no-build postgres
"${compose[@]}" run --rm --no-deps migrate

if [[ "$mode" == "first-upgrade" ]]; then
  echo "Removing only the preflight-validated legacy application containers; named volumes are untouched."
  for container in football-collector football-n8n football-adminer; do
    if docker container inspect "$container" >/dev/null 2>&1; then
      docker container stop "$container"
      docker container rm "$container"
    fi
  done
fi

echo "Starting Foundation services; --remove-orphans is safe after project/volume preflight."
if ! "${compose[@]}" up -d --remove-orphans --no-build --no-deps postgres api worker frontend proxy \
  || ! ./scripts/verify-health.sh; then
  echo "Deployment health failed; invoking the validated rollback target." >&2
  ./scripts/rollback.sh || true
  exit 1
fi

printf '%s\n' "$target_revision" > .deployed-revision
printf '%s\n' "$target_revision" > .foundation-deployed
echo "Deployment complete. Persistent PostgreSQL and n8n volumes were not removed."
