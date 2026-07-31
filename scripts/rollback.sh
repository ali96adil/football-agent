#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Rollback stops only application containers; it never deletes volumes or restores data automatically."
echo "To restore a reviewed backup into an isolated database, see docs/upgrade-v1-foundation.md."
docker compose stop proxy frontend api worker || true
echo "Checkout the previous Git revision, run its documented compose up command, then verify health."
echo "Never run: docker compose down -v"
