#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
root="$PWD"
dry_run=0
[[ "${1:-}" == "--dry-run" ]] && dry_run=1
[[ -z "${1:-}" || "${1:-}" == "--dry-run" ]] || { echo "Usage: $0 [--dry-run]" >&2; exit 2; }

test -f .env || { echo "Rollback blocked: .env is missing." >&2; exit 1; }
python3 scripts/check_env_names.py .env \
  TZ POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD APP_DB_NAME APP_DB_USER APP_DB_PASSWORD
test -s .last-known-good-revision || {
  echo "Rollback blocked: .last-known-good-revision is missing or empty." >&2
  exit 1
}
revision="$(tr -d '[:space:]' < .last-known-good-revision)"
git cat-file -e "$revision^{commit}" 2>/dev/null || {
  echo "Rollback blocked: recorded revision is not present in the local Git object database." >&2
  exit 1
}
git show "$revision:compose.yaml" >/dev/null 2>&1 || {
  echo "Rollback blocked: recorded revision has no compose.yaml." >&2
  exit 1
}

if [[ "$dry_run" == "1" ]]; then
  echo "DRY RUN: revision and release manifest are available; no container was changed."
  exit 0
fi

release_dir="$(mktemp -d)"
cleanup() { rm -rf -- "$release_dir"; }
trap cleanup EXIT
git archive "$revision" | tar -x -C "$release_dir"
previous=(docker compose --project-name football-agent --project-directory "$release_dir" \
  --env-file "$root/.env" -f "$release_dir/compose.yaml")
current=(docker compose --env-file "$root/.env" -f "$root/compose.yaml")

echo "Preparing previous release before replacing the current release."
"${previous[@]}" config --quiet
"${previous[@]}" pull --ignore-buildable --policy missing
"${previous[@]}" build

verify_previous_release() {
  local deadline=$((SECONDS + 120))
  while (( SECONDS < deadline )); do
    local failed=0 count=0
    while read -r container_id; do
      [[ -n "$container_id" ]] || continue
      count=$((count + 1))
      local service status health exit_code
      service="$(docker container inspect --format '{{ index .Config.Labels "com.docker.compose.service" }}' "$container_id")"
      status="$(docker container inspect --format '{{ .State.Status }}' "$container_id")"
      health="$(docker container inspect --format '{{ if .State.Health }}{{ .State.Health.Status }}{{ else }}none{{ end }}' "$container_id")"
      exit_code="$(docker container inspect --format '{{ .State.ExitCode }}' "$container_id")"
      if [[ "$service" == "migrate" && "$status" == "exited" && "$exit_code" == "0" ]]; then
        continue
      fi
      [[ "$status" == "running" && "$health" != "unhealthy" ]] || failed=1
      [[ "$health" != "starting" ]] || failed=1
    done < <("${previous[@]}" ps -aq)
    [[ "$count" -gt 0 && "$failed" -eq 0 ]] && return 0
    sleep 5
  done
  return 1
}

echo "Restoring recorded release $revision. Database migrations are intentionally left in place."
if "${previous[@]}" up -d --remove-orphans --no-build && verify_previous_release; then
  printf '%s\n' "$revision" > .deployed-revision
  echo "Rollback succeeded and the previous release is healthy."
  exit 0
fi

echo "ROLLBACK FAILED. Attempting to restore the current Foundation services so the host is not left stopped." >&2
if "${current[@]}" up -d --remove-orphans --no-build postgres api worker frontend proxy \
  && "$root/scripts/verify-health.sh"; then
  echo "Rescue succeeded: current Foundation release is running. Inspect previous-release build and container logs before retrying." >&2
else
  echo "RESCUE FAILED: inspect 'docker compose --env-file .env ps -a' and logs for postgres, api, frontend, and proxy. Do not run any volume-deleting Compose command." >&2
fi
exit 1
