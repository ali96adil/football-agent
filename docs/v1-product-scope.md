# Football Agent v1 product scope

The `v1/product` line builds the actual product on top of Foundation commit
`6bcbb87172f31d42cfa995b2968451b23a7f7399`. Foundation remains the runtime
and data-pipeline base; it is not a completed v1 product.

## Release stages

### 1.0.0-dev.2 — Authentication and RBAC

- Real local-user login with server-side sessions in PostgreSQL.
- `admin`, `operator`, and `viewer` roles enforced by backend dependencies.
- HttpOnly/SameSite session cookies, CSRF protection, login throttling, secure
  password hashing, and an audit log.
- Interactive first-admin command with no default credential in source.
- Additive, data-preserving migrations and permission-matrix tests.

### 1.0.0-dev.3 — Product UI and operations

- New responsive Arabic RTL product shell and login experience.
- Dashboard, fixtures, predictions, sources, worker/jobs, administration,
  users/roles, audit log, and settings pages.
- Authorized controls for sync, snapshots, predictions, evaluation, retry,
  sources, and scheduling, with confirmation and asynchronous job progress.
- Always show the development version, deployed Git revision, current user,
  data provenance/freshness, sources, worker, and last successful sync.
- Production views use database/API data only; no mock records.

### 1.0.0-dev.4 — Telegram

- Long-polling bot by default, configured only through secrets.
- User/chat allowlist and role-aware read/control commands.
- Operational alerts for providers, worker heartbeat, stale data, failed jobs,
  and configured successful runs.
- Control commands are written to the same audit log; CI uses mocked transport.

### 1.0.0-dev.5 — Integration and deployment candidate

- Unit, PostgreSQL integration, auth/RBAC, UI/RTL, operations, Telegram,
  migration, Compose, and release checks.
- Native ARM64 collector/frontend builds and full health verification.
- Preserve PostgreSQL and n8n volumes and validate entity counts before/after.
- Publish only the proxy on `0.0.0.0:8088`; API and PostgreSQL stay internal.
- Deploy application services only and keep `.deployed-revision`, API, and UI
  aligned with the actual local commit.

## Completion rule

The version remains a development version through `1.0.0-dev.5`. It must not
be renamed to `1.0.0` until functional acceptance is complete.
