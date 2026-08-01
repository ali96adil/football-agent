ALTER TABLE core.jobs
    ADD COLUMN IF NOT EXISTS result JSONB,
    ADD COLUMN IF NOT EXISTS requested_by UUID REFERENCES core.users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS requested_via TEXT NOT NULL DEFAULT 'scheduler'
        CHECK (requested_via IN ('scheduler', 'web', 'telegram', 'system'));

CREATE TABLE IF NOT EXISTS core.system_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES core.users(id) ON DELETE SET NULL
);

INSERT INTO core.system_settings (key, value, description)
VALUES
    ('sync_interval_seconds', '3600'::jsonb, 'Native scheduler interval in seconds.'),
    ('telegram_success_alerts', 'false'::jsonb, 'Send successful operation alerts when Telegram is enabled.'),
    ('stale_data_minutes', '180'::jsonb, 'Age threshold used by UI and operational alerts.')
ON CONFLICT (key) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_jobs_requested_by ON core.jobs (requested_by, created_at DESC);
