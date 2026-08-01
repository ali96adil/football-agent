#!/usr/bin/env bash
set -euo pipefail

image="${1:?usage: validate_frontend_arm64_runtime.sh IMAGE}"

architecture="$(docker image inspect --format '{{.Architecture}}' "$image")"
operating_system="$(docker image inspect --format '{{.Os}}' "$image")"
[[ "$architecture" == "arm64" ]] || {
  echo "Expected an ARM64 image, got architecture '$architecture'." >&2
  exit 1
}
[[ "$operating_system" == "linux" ]] || {
  echo "Expected a Linux image, got operating system '$operating_system'." >&2
  exit 1
}

# Exercise sharp and reject every non-ARM64 ELF copied into the application.
# This catches unsafe x86 standalone output even when node itself starts.
docker run --rm --platform linux/arm64 --entrypoint node -i "$image" - <<'NODE'
const fs = require("node:fs");
const path = require("node:path");

if (process.platform !== "linux" || process.arch !== "arm64") {
  throw new Error(`unexpected runtime ${process.platform}/${process.arch}`);
}

const pending = ["/app"];
const wrongArchitecture = [];
let elfCount = 0;

while (pending.length > 0) {
  const current = pending.pop();
  for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
    const candidate = path.join(current, entry.name);
    if (entry.isDirectory()) {
      pending.push(candidate);
      continue;
    }
    if (!entry.isFile()) continue;

    const descriptor = fs.openSync(candidate, "r");
    try {
      const header = Buffer.alloc(20);
      const bytesRead = fs.readSync(descriptor, header, 0, header.length, 0);
      if (bytesRead < 20 || !header.subarray(0, 4).equals(Buffer.from([0x7f, 0x45, 0x4c, 0x46]))) {
        continue;
      }
      elfCount += 1;
      const machine = header[5] === 2 ? header.readUInt16BE(18) : header.readUInt16LE(18);
      if (machine !== 183) wrongArchitecture.push(`${candidate} (ELF machine ${machine})`);
    } finally {
      fs.closeSync(descriptor);
    }
  }
}

if (wrongArchitecture.length > 0) {
  throw new Error(`non-ARM64 native files found:\n${wrongArchitecture.join("\n")}`);
}
if (elfCount === 0) throw new Error("no native runtime files were inspected");

const sharp = require("sharp");
async function validateSharp() {
  await sharp({ create: { width: 1, height: 1, channels: 4, background: "#000000" } })
    .png()
    .toBuffer();
  console.log(`validated ${elfCount} ARM64 ELF files and sharp ${sharp.versions.sharp}`);
}

validateSharp().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
NODE

container_name="football-frontend-arm64-smoke-$$"
cleanup() {
  docker rm -f "$container_name" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run --detach --rm --platform linux/arm64 \
  --name "$container_name" --publish 127.0.0.1::3000 "$image" >/dev/null

host_port="$(docker port "$container_name" 3000/tcp | sed -n 's/.*://p' | head -n 1)"
[[ -n "$host_port" ]] || {
  echo "Docker did not publish the frontend smoke-test port." >&2
  exit 1
}

health="starting"
for _ in $(seq 1 30); do
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' "$container_name")"
  case "$health" in
    healthy) break ;;
    unhealthy|missing)
      docker logs "$container_name" >&2 || true
      echo "Frontend container health is '$health'." >&2
      exit 1
      ;;
  esac
  sleep 2
done

[[ "$health" == "healthy" ]] || {
  docker logs "$container_name" >&2 || true
  echo "Frontend container did not become healthy; last status was '$health'." >&2
  exit 1
}

curl --fail --silent --show-error --max-time 10 \
  "http://127.0.0.1:${host_port}/" >/dev/null
echo "ARM64 frontend image architecture, native modules, healthcheck, and HTTP runtime passed."
