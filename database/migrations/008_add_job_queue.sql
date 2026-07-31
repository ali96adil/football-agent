BEGIN;

CREATE TABLE IF NOT EXISTS core.schema_migrations (
    version TEXT PRIMARY KEY,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS core.jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN (
        'queued', 'running', 'succeeded', 'failed', 'retry', 'dead_letter'
    )),
    idempotency_key TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts > 0),
    run_after TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    timeout_seconds INTEGER NOT NULL DEFAULT 300 CHECK (timeout_seconds > 0),
    lease_expires_at TIMESTAMPTZ,
    heartbeat_at TIMESTAMPTZ,
    locked_by TEXT,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (job_type, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_jobs_claimable
    ON core.jobs (status, run_after, created_at)
    WHERE status IN ('queued', 'retry');

CREATE INDEX IF NOT EXISTS idx_jobs_leases
    ON core.jobs (lease_expires_at)
    WHERE status = 'running';

COMMENT ON TABLE core.jobs IS
    'Durable PostgreSQL queue. Claims use FOR UPDATE SKIP LOCKED; workers renew a lease heartbeat.';

COMMIT;
