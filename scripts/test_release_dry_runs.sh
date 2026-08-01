#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

for script in scripts/*.sh; do
  if grep -Eq '(^|[;[:space:]])(source|\.)[[:space:]]+.*\.env' "$script"; then
    echo "Unsafe .env sourcing found in $script" >&2
    exit 1
  fi
  if [[ "$script" != "scripts/test_release_dry_runs.sh" ]] \
    && grep -Eq 'docker[[:space:]]+compose.*[[:space:]]down[[:space:]]+-v' "$script"; then
    echo "Volume-deleting Compose command found in $script" >&2
    exit 1
  fi
done

state_dir="$(mktemp -d)"
had_revision=0
if [[ -f .last-known-good-revision ]]; then
  had_revision=1
  cp .last-known-good-revision "$state_dir/last-known-good-revision"
fi
cleanup() {
  if [[ "$had_revision" == "1" ]]; then
    cp "$state_dir/last-known-good-revision" .last-known-good-revision
  else
    rm -f .last-known-good-revision
  fi
  rm -rf -- "$state_dir"
}
trap cleanup EXIT
# A dry-run only needs a locally available commit containing compose.yaml.
# HEAD works in pull requests, normal local checkouts, and depth-1 clones.
git rev-parse HEAD > .last-known-good-revision

PREFLIGHT_SKIP_RUNTIME=1 ./scripts/deploy.sh --first-upgrade --dry-run \
  | grep -q "no containers were stopped or changed"
./scripts/rollback.sh --dry-run | grep -q "no container was changed"
./scripts/test_deploy_health_scenarios.sh
echo "Deploy and rollback dry-run safety tests passed."
