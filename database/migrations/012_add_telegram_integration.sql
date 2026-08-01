CREATE TABLE IF NOT EXISTS core.telegram_identities (
    chat_id BIGINT PRIMARY KEY,
    telegram_user_id BIGINT,
    user_id UUID NOT NULL REFERENCES core.users(id) ON DELETE CASCADE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    alerts JSONB NOT NULL DEFAULT '{"failures":true,"worker":true,"stale_data":true,"success":false}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (telegram_user_id)
);

COMMENT ON TABLE core.telegram_identities IS
    'Explicit Telegram allowlist mapped to current product users and RBAC roles.';
