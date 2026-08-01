CREATE TABLE IF NOT EXISTS core.worker_heartbeats (
    worker_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('idle', 'running', 'stopping')),
    heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    current_job_id UUID REFERENCES core.jobs(id) ON DELETE SET NULL,
    scheduler_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    schedule_interval_seconds INTEGER NOT NULL CHECK (schedule_interval_seconds > 0),
    next_sync_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_worker_heartbeats_freshness
    ON core.worker_heartbeats (heartbeat_at DESC);

COMMENT ON TABLE core.worker_heartbeats IS
    'Process heartbeat and scheduler state for Foundation workers.';
