ALTER TABLE core.telegram_identities
    DROP CONSTRAINT IF EXISTS telegram_identities_pkey,
    DROP CONSTRAINT IF EXISTS telegram_identities_telegram_user_id_key;

ALTER TABLE core.telegram_identities
    ALTER COLUMN telegram_user_id SET NOT NULL,
    ADD CONSTRAINT telegram_identities_pkey
        PRIMARY KEY (chat_id, telegram_user_id);

CREATE TABLE core.telegram_destinations (
    chat_id BIGINT PRIMARY KEY,
    title TEXT NOT NULL CHECK (char_length(title) BETWEEN 1 AND 255),
    chat_type TEXT NOT NULL CHECK (chat_type IN ('private', 'group', 'supergroup', 'channel')),
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    publish_prediction_new BOOLEAN NOT NULL DEFAULT FALSE,
    publish_prediction_changed BOOLEAN NOT NULL DEFAULT FALSE,
    publish_update_success BOOLEAN NOT NULL DEFAULT FALSE,
    publish_update_failure BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES core.users(id) ON DELETE SET NULL
);

CREATE TABLE core.telegram_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    destination_chat_id BIGINT NOT NULL
        REFERENCES core.telegram_destinations(chat_id) ON DELETE CASCADE,
    event_key TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'prediction_new', 'prediction_changed',
        'update_success', 'update_failure'
    )),
    content_hash TEXT NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    event_occurred_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'claimed'
        CHECK (status IN ('claimed', 'sent', 'failed')),
    claimed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    failure_code TEXT,
    UNIQUE (destination_chat_id, event_key, content_hash)
);

CREATE INDEX idx_telegram_deliveries_event
    ON core.telegram_deliveries (event_key, sent_at DESC);

COMMENT ON TABLE core.telegram_identities IS
    'Command allowlist: an exact Telegram chat and sender pair maps to product RBAC.';
COMMENT ON TABLE core.telegram_destinations IS
    'Independent, administrator-managed publication destinations and subscriptions.';
COMMENT ON TABLE core.telegram_deliveries IS
    'Durable claims and delivery outcomes used to prevent backlog and duplicate publication.';
