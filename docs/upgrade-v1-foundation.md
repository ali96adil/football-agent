# v1 Foundation upgrade (Raspberry Pi)

Foundation preserves both named data volumes:

- `football_postgres_data`
- `football_n8n_data`

No deployment or rollback command removes volumes. PostgreSQL has no host port
and is attached only to the internal `football_private` network. `proxy` is the
only service that publishes a host port. API, worker, and frontend use the
non-publishing `football_egress` network for provider APIs, Telegram, and
remote assets.

## Database and environment identity

The existing PostgreSQL volume was bootstrapped with `POSTGRES_DB=n8n` and
`POSTGRES_USER=n8n`; preserve those values. The application database remains:

```text
database: football_intelligence
owner:    football_app
```

Copy missing names from `.env.example`, but never make `.env` a shell script.
The release scripts use `docker compose --env-file .env`; they do not `source`
it and never print secrets during preflight.

## First upgrade from the legacy Pi stack

This is the only path that removes the old `football-collector`,
`football-n8n`, and `football-adminer` containers. Their named volumes are not
removed. Before checking out Foundation, record the known-good legacy commit:

```bash
cd ~/football-agent
git status --short
git rev-parse HEAD > .last-known-good-revision
git checkout v1/foundation
```

Merge the new required names into the existing `.env`, retaining the real
`POSTGRES_*` and n8n encryption values. Validate without changing containers:

```bash
PREFLIGHT_SKIP_RUNTIME=1 ./scripts/deploy.sh --first-upgrade --dry-run
./scripts/preflight.sh --first-upgrade
```

The real preflight proves all of the following before legacy containers can be
stopped:

- Compose project name is exactly `football-agent`;
- `football-postgres` and any legacy named containers belong to that project;
- PostgreSQL is mounted from `football_postgres_data`;
- n8n, when present, is mounted from `football_n8n_data`;
- the rendered Compose model passes proxy-only ports and network assertions.

Deploy only after that validation:

```bash
./scripts/deploy.sh --first-upgrade
```

The script pulls base/runtime images and completes all production builds before
the backup or any container removal. It backs up `football_intelligence`, runs
atomic migrations, removes only the preflight-validated legacy application
containers, then uses `up --remove-orphans`. It never removes a volume.

## Later Foundation upgrades

After the first successful deployment, use the regular path:

```bash
./scripts/deploy.sh --dry-run
./scripts/deploy.sh
```

Regular preflight requires `.foundation-deployed`. Before replacing services,
the script moves the previously deployed revision into
`.last-known-good-revision`; after health succeeds it records the new revision
in `.deployed-revision`. It repeats pull/build, backup, migration, and health
verification on every upgrade.

## Migration atomicity and legacy SQL

The runner connects in autocommit mode only so it can explicitly own every
transaction. Each pending migration executes together with its
`schema_migrations` checksum insert in one short outer transaction. Failure at
either step rolls back both schema and checksum record.

Files `001_core_schema.sql`, `006_add_team_snapshots.sql`,
`007_add_overall_rating.sql`, and `008_add_job_queue.sql` contain historical
standalone `BEGIN`/`COMMIT` controls. They may already be recorded on databases,
so their bytes and checksums are intentionally unchanged. The runner recognizes
only the exact legacy control sequence for those versions and removes those
lines in memory before execution. Any new migration containing transaction
control is rejected. This preserves existing checksums while giving the runner
sole transaction ownership.

## Frontend image behavior

The production frontend root filesystem stays read-only. Next image
optimization is disabled so the Pi does not need a writable `.next/cache` or
spend CPU optimizing crests. Allowed HTTPS images are served unoptimized; the
frontend retains egress for remote assets.

## Rollback

```bash
./scripts/rollback.sh --dry-run
./scripts/rollback.sh
```

Rollback validates `.last-known-good-revision`, proves the commit and its
Compose manifest exist locally, archives that release to a temporary directory,
and completes its pull/build before replacing the current services. It then
starts the recorded release with the same Compose project and checks container
state/health.

Schema migrations are never reversed automatically. Migration 008 is additive;
leaving it in place is safer than a destructive downgrade. If the previous
release fails to start, rollback attempts to restore and health-check the
current Foundation services and prints explicit rescue commands/status. It
never uses a volume-deleting operation.

For a data restore, restore a selected dump into an isolated database first.
Overwriting production data requires a separate reviewed procedure and explicit
approval.
