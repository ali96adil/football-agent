# Football Intelligence

The v1 foundation runs a lightweight, ARM64-compatible Docker architecture on
a Raspberry Pi:

| Service | Responsibility | Host port |
| --- | --- | --- |
| `proxy` (Caddy) | local HTTP routing to UI and `/api` | the only published port |
| `frontend` | production Next.js application | none |
| `api` | FastAPI HTTP endpoints | none |
| `worker` | durable background jobs | none |
| `postgres` | database | none |

`n8n` is retained under the `automation` profile and Adminer under `tools`; they
are not started by default and neither volume is deleted.

Why Caddy: its official Alpine image supports ARM64, the local routing config is
small, and it avoids the extra configuration footprint of Nginx for this phase.

## Job queue guarantees

`core.jobs` provides queued/running/succeeded/failed/retry/dead-letter states,
idempotency keys, attempt limits, leases, heartbeats, timeouts, and timestamps.
Workers claim with `FOR UPDATE SKIP LOCKED`. After a power loss, expired leases
become `retry` or `dead_letter` safely. The API process does not consume jobs.

## Local development and validation

```bash
cd services/collector
python -m unittest discover -s tests -p 'test_*.py'
cd ../../frontend
npm ci
npm run lint
npm run build
```

For Pi installation, follow [the upgrade guide](docs/upgrade-v1-foundation.md).
Never use `docker compose down -v` for this project.
