#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

test "$({ rg -l '(^|[;[:space:]])(source|\.)[[:space:]]+.*\.env' scripts/*.sh || true; } | wc -l)" -eq 0
test "$({ rg -l 'docker[[:space:]]+compose.*[[:space:]]down[[:space:]]+-v' scripts/*.sh --glob '!test_release_dry_runs.sh' || true; } | wc -l)" -eq 0

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
git rev-parse 25f9f27 > .last-known-good-revision

PREFLIGHT_SKIP_RUNTIME=1 ./scripts/deploy.sh --first-upgrade --dry-run \
  | grep -q "no containers were stopped or changed"
./scripts/rollback.sh --dry-run | grep -q "no container was changed"
echo "Deploy and rollback dry-run safety tests passed."
