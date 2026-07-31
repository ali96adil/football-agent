# v1 Foundation upgrade (Raspberry Pi)

This PR is deliberately reversible. It does not delete `n8n`, Adminer, the
existing PostgreSQL volume, or Football Intelligence data.

## Important database identity

The existing PostgreSQL container was initialized with `POSTGRES_DB=n8n` and
`POSTGRES_USER=n8n`. Those variables are bootstrap compatibility settings only.
Every backup, migration, and verification in this release explicitly targets:

```text
database: football_intelligence
owner:    football_app
```

Never replace `APP_DB_*` with `POSTGRES_*`, and never run `docker compose down -v`.

## Upgrade steps on the Pi

1. Make sure the old project is healthy and keep its Git revision:

   ```bash
   cd ~/football-agent
   git status --short
   git rev-parse HEAD > .last-known-good-revision
   git fetch origin
   git checkout v1/foundation
   git pull --ff-only
   ```

2. Preserve your current `.env`, then merge only the new explicit values from
   `.env.example`. Retain the existing `POSTGRES_*` values. Set:

   ```dotenv
   APP_DB_NAME=football_intelligence
   APP_DB_USER=football_app
   APP_DB_PASSWORD=<the existing football_app password>
   PROXY_BIND_ADDRESS=127.0.0.1
   PROXY_HTTP_PORT=8088
   ```

3. Run the read-only safety check:

   ```bash
   chmod +x scripts/*.sh
   ./scripts/preflight.sh
   ```

4. Deploy. This creates `backups/football_intelligence-<timestamp>.dump`, runs
   checksum-protected migrations, and replaces only application containers.

   ```bash
   ./scripts/deploy.sh
   ```

5. Verify locally before exposing the domain:

   ```bash
   ./scripts/verify-health.sh
   docker compose ps
   docker compose logs --tail=100 proxy api worker
   ```

At this point the host has only one published port: `127.0.0.1:8088` from
`proxy`. For a domain, put an external reverse proxy or later TLS configuration
in front of this port. Cloudflare Tunnel is intentionally not part of this PR.

## n8n and Adminer

They are moved to Compose profiles and are not started by a normal
`docker compose up -d`. Their volumes are unchanged. To use them temporarily:

```bash
docker compose --profile automation up -d n8n
docker compose --profile tools up -d adminer
```

Do not delete either service or volume until the separately documented
inventory, encrypted backup, isolated restore, and dependency observation have
all passed.

## Rollback

`./scripts/rollback.sh` stops only `proxy`, `frontend`, `api`, and `worker`.
It does not alter PostgreSQL. To restore application containers, check out the
revision recorded in `.last-known-good-revision` and use that revision's normal
Compose startup. Migration 008 only adds tables/indexes and is safe to leave in
place; no automatic destructive downgrade exists.

If a data restore is ever needed, first create an isolated database (never
overwrite production), restore the selected `football_intelligence` dump there,
and validate it. A production restore needs an explicit, separate approval.
