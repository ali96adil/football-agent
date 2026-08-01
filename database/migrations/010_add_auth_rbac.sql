CREATE TABLE IF NOT EXISTS core.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'operator', 'viewer')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    CONSTRAINT users_username_normalized CHECK (username = lower(username)),
    CONSTRAINT users_username_format CHECK (username ~ '^[a-z0-9][a-z0-9_.-]{2,63}$'),
    UNIQUE (username)
);

CREATE TABLE IF NOT EXISTS core.user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES core.users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    csrf_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    client_ip INET,
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_active
    ON core.user_sessions (token_hash, expires_at) WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS core.login_attempts (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    client_ip INET,
    succeeded BOOLEAN NOT NULL,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_login_attempts_throttle
    ON core.login_attempts (username, client_ip, attempted_at DESC);

CREATE TABLE IF NOT EXISTS core.audit_log (
    id BIGSERIAL PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_user_id UUID REFERENCES core.users(id) ON DELETE SET NULL,
    actor_username TEXT,
    actor_role TEXT,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    outcome TEXT NOT NULL CHECK (outcome IN ('success', 'denied', 'failure')),
    client_ip INET,
    details JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_audit_log_recent ON core.audit_log (occurred_at DESC);

COMMENT ON TABLE core.users IS 'Local product identities with backend-enforced RBAC.';
COMMENT ON TABLE core.user_sessions IS 'Revocable server-side browser sessions; raw tokens are never stored.';
COMMENT ON TABLE core.audit_log IS 'Security and administrative control audit trail.';
