BEGIN;

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS model;
CREATE SCHEMA IF NOT EXISTS audit;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =========================================================
-- مصادر البيانات وميزانيات الطلبات
-- =========================================================

CREATE TABLE IF NOT EXISTS core.data_sources (
    id                  BIGSERIAL PRIMARY KEY,
    code                TEXT NOT NULL UNIQUE,
    name                TEXT NOT NULL,
    source_type         TEXT NOT NULL CHECK (
                            source_type IN (
                                'api',
                                'official_site',
                                'news',
                                'scraper',
                                'weather',
                                'market',
                                'manual'
                            )
                        ),
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    priority            SMALLINT NOT NULL DEFAULT 50
                            CHECK (priority BETWEEN 0 AND 100),
    reliability_score   NUMERIC(5,4)
                            CHECK (
                                reliability_score IS NULL OR
                                reliability_score BETWEEN 0 AND 1
                            ),
    daily_request_limit INTEGER,
    reserved_requests   INTEGER NOT NULL DEFAULT 0,
    requests_used_today INTEGER NOT NULL DEFAULT 0,
    last_success_at     TIMESTAMPTZ,
    last_failure_at     TIMESTAMPTZ,
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================================================
-- البطولات والمواسم
-- =========================================================

CREATE TABLE IF NOT EXISTS core.competitions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name  TEXT NOT NULL,
    country_code    TEXT,
    competition_type TEXT,
    gender          TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (canonical_name, country_code)
);

CREATE TABLE IF NOT EXISTS core.seasons (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competition_id  UUID NOT NULL
                        REFERENCES core.competitions(id)
                        ON DELETE CASCADE,
    label           TEXT NOT NULL,
    starts_on       DATE,
    ends_on         DATE,
    is_current      BOOLEAN NOT NULL DEFAULT FALSE,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (competition_id, label)
);

-- =========================================================
-- الفرق وهوياتها عبر المصادر
-- =========================================================

CREATE TABLE IF NOT EXISTS core.teams (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name  TEXT NOT NULL,
    short_name      TEXT,
    country_code    TEXT,
    founded_year    INTEGER,
    logo_url        TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS core.team_source_ids (
    id               BIGSERIAL PRIMARY KEY,
    team_id           UUID NOT NULL
                         REFERENCES core.teams(id)
                         ON DELETE CASCADE,
    source_id         BIGINT NOT NULL
                         REFERENCES core.data_sources(id)
                         ON DELETE CASCADE,
    external_team_id  TEXT NOT NULL,
    source_name       TEXT,
    confidence        NUMERIC(5,4) NOT NULL DEFAULT 1
                         CHECK (confidence BETWEEN 0 AND 1),
    verified          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_id, external_team_id)
);

CREATE TABLE IF NOT EXISTS core.team_aliases (
    id              BIGSERIAL PRIMARY KEY,
    team_id         UUID NOT NULL
                        REFERENCES core.teams(id)
                        ON DELETE CASCADE,
    alias           TEXT NOT NULL,
    language_code   TEXT,
    source_id       BIGINT
                        REFERENCES core.data_sources(id)
                        ON DELETE SET NULL,
    normalized_alias TEXT NOT NULL,
    UNIQUE (normalized_alias, team_id)
);

-- =========================================================
-- المباريات
-- =========================================================

CREATE TABLE IF NOT EXISTS core.fixtures (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competition_id      UUID
                            REFERENCES core.competitions(id)
                            ON DELETE SET NULL,
    season_id           UUID
                            REFERENCES core.seasons(id)
                            ON DELETE SET NULL,
    home_team_id        UUID NOT NULL
                            REFERENCES core.teams(id),
    away_team_id        UUID NOT NULL
                            REFERENCES core.teams(id),
    kickoff_at          TIMESTAMPTZ NOT NULL,
    venue_name          TEXT,
    venue_city          TEXT,
    neutral_venue       BOOLEAN NOT NULL DEFAULT FALSE,
    fixture_status      TEXT NOT NULL DEFAULT 'scheduled',
    home_score          SMALLINT,
    away_score          SMALLINT,
    extra_time_home     SMALLINT,
    extra_time_away     SMALLINT,
    penalties_home      SMALLINT,
    penalties_away      SMALLINT,
    winner_team_id      UUID
                            REFERENCES core.teams(id)
                            ON DELETE SET NULL,
    result_confirmed    BOOLEAN NOT NULL DEFAULT FALSE,
    selection_score     NUMERIC(6,3),
    data_completeness   NUMERIC(5,4)
                            CHECK (
                                data_completeness IS NULL OR
                                data_completeness BETWEEN 0 AND 1
                            ),
    source_quality      NUMERIC(5,4)
                            CHECK (
                                source_quality IS NULL OR
                                source_quality BETWEEN 0 AND 1
                            ),
    selected_for_analysis BOOLEAN NOT NULL DEFAULT FALSE,
    selection_rank      SMALLINT,
    rejection_reason    TEXT,
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (home_team_id <> away_team_id)
);

CREATE INDEX IF NOT EXISTS idx_fixtures_kickoff
    ON core.fixtures(kickoff_at);

CREATE INDEX IF NOT EXISTS idx_fixtures_selected
    ON core.fixtures(kickoff_at, selected_for_analysis);

CREATE INDEX IF NOT EXISTS idx_fixtures_teams
    ON core.fixtures(home_team_id, away_team_id);

CREATE TABLE IF NOT EXISTS core.fixture_source_ids (
    id                  BIGSERIAL PRIMARY KEY,
    fixture_id          UUID NOT NULL
                            REFERENCES core.fixtures(id)
                            ON DELETE CASCADE,
    source_id           BIGINT NOT NULL
                            REFERENCES core.data_sources(id)
                            ON DELETE CASCADE,
    external_fixture_id TEXT NOT NULL,
    source_status       TEXT,
    source_kickoff_at   TIMESTAMPTZ,
    last_synced_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload_hash        TEXT,
    UNIQUE (source_id, external_fixture_id)
);

-- =========================================================
-- تخزين الاستجابات الخام
-- =========================================================

CREATE TABLE IF NOT EXISTS raw.api_payloads (
    id              BIGSERIAL PRIMARY KEY,
    source_id       BIGINT NOT NULL
                        REFERENCES core.data_sources(id)
                        ON DELETE CASCADE,
    fixture_id      UUID
                        REFERENCES core.fixtures(id)
                        ON DELETE SET NULL,
    endpoint        TEXT NOT NULL,
    request_key     TEXT,
    requested_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    response_status INTEGER,
    payload         JSONB,
    payload_hash    TEXT,
    expires_at      TIMESTAMPTZ,
    error_message   TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_raw_payload_fixture
    ON raw.api_payloads(fixture_id, requested_at DESC);

CREATE INDEX IF NOT EXISTS idx_raw_payload_expiry
    ON raw.api_payloads(expires_at)
    WHERE expires_at IS NOT NULL;

-- =========================================================
-- الخصائص الرقمية المستخرجة
-- =========================================================

CREATE TABLE IF NOT EXISTS model.feature_snapshots (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fixture_id          UUID NOT NULL
                            REFERENCES core.fixtures(id)
                            ON DELETE CASCADE,
    snapshot_type       TEXT NOT NULL CHECK (
                            snapshot_type IN (
                                'discovery',
                                'early',
                                'prematch',
                                'lineup',
                                'postmatch'
                            )
                        ),
    captured_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data_cutoff_at      TIMESTAMPTZ NOT NULL,
    feature_version     TEXT NOT NULL,
    data_completeness   NUMERIC(5,4) NOT NULL
                            CHECK (data_completeness BETWEEN 0 AND 1),
    source_quality      NUMERIC(5,4) NOT NULL
                            CHECK (source_quality BETWEEN 0 AND 1),
    source_agreement    NUMERIC(5,4)
                            CHECK (
                                source_agreement IS NULL OR
                                source_agreement BETWEEN 0 AND 1
                            ),
    features            JSONB NOT NULL,
    feature_hash        TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (fixture_id, snapshot_type, feature_hash)
);

CREATE INDEX IF NOT EXISTS idx_feature_fixture_time
    ON model.feature_snapshots(fixture_id, captured_at DESC);

-- =========================================================
-- إصدارات النماذج والأوزان
-- =========================================================

CREATE TABLE IF NOT EXISTS model.model_versions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name          TEXT NOT NULL,
    version             TEXT NOT NULL,
    model_family        TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'candidate'
                            CHECK (
                                status IN (
                                    'candidate',
                                    'active',
                                    'retired',
                                    'rejected'
                                )
                            ),
    training_started_at TIMESTAMPTZ,
    training_ended_at   TIMESTAMPTZ,
    training_matches    INTEGER,
    validation_matches  INTEGER,
    test_matches        INTEGER,
    metrics             JSONB NOT NULL DEFAULT '{}'::jsonb,
    configuration       JSONB NOT NULL DEFAULT '{}'::jsonb,
    artifact_path       TEXT,
    parent_version_id   UUID
                            REFERENCES model.model_versions(id)
                            ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (model_name, version)
);

CREATE TABLE IF NOT EXISTS model.model_weights (
    id               BIGSERIAL PRIMARY KEY,
    model_version_id UUID NOT NULL
                         REFERENCES model.model_versions(id)
                         ON DELETE CASCADE,
    prediction_target TEXT NOT NULL,
    component_name    TEXT NOT NULL,
    weight_value      NUMERIC(12,8) NOT NULL,
    metadata          JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (
        model_version_id,
        prediction_target,
        component_name
    )
);

-- =========================================================
-- توقعات النماذج
-- =========================================================

CREATE TABLE IF NOT EXISTS model.predictions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fixture_id              UUID NOT NULL
                                REFERENCES core.fixtures(id)
                                ON DELETE CASCADE,
    feature_snapshot_id     UUID NOT NULL
                                REFERENCES model.feature_snapshots(id),
    model_version_id        UUID
                                REFERENCES model.model_versions(id)
                                ON DELETE SET NULL,
    prediction_stage        TEXT NOT NULL CHECK (
                                prediction_stage IN (
                                    'early',
                                    'prematch',
                                    'lineup'
                                )
                            ),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    home_win_probability    NUMERIC(7,6) NOT NULL,
    draw_probability        NUMERIC(7,6) NOT NULL,
    away_win_probability    NUMERIC(7,6) NOT NULL,
    expected_home_goals     NUMERIC(7,4),
    expected_away_goals     NUMERIC(7,4),
    predicted_home_score    SMALLINT,
    predicted_away_score    SMALLINT,
    over_2_5_probability    NUMERIC(7,6),
    both_teams_score_probability NUMERIC(7,6),
    calibrated_confidence   NUMERIC(5,4)
                                CHECK (
                                    calibrated_confidence IS NULL OR
                                    calibrated_confidence BETWEEN 0 AND 1
                                ),
    publish_decision        BOOLEAN NOT NULL DEFAULT FALSE,
    abstention_reason       TEXT,
    explanation             JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw_model_output        JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (
        ABS(
            home_win_probability +
            draw_probability +
            away_win_probability - 1
        ) < 0.001
    )
);

CREATE INDEX IF NOT EXISTS idx_predictions_fixture_stage
    ON model.predictions(fixture_id, prediction_stage, created_at DESC);

-- =========================================================
-- قرارات الوكلاء ومجلس الوكلاء
-- =========================================================

CREATE TABLE IF NOT EXISTS audit.agent_decisions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fixture_id          UUID
                            REFERENCES core.fixtures(id)
                            ON DELETE CASCADE,
    prediction_id       UUID
                            REFERENCES model.predictions(id)
                            ON DELETE CASCADE,
    agent_name          TEXT NOT NULL,
    agent_version       TEXT NOT NULL,
    decision_type       TEXT NOT NULL,
    decision            TEXT NOT NULL,
    confidence          NUMERIC(5,4)
                            CHECK (
                                confidence IS NULL OR
                                confidence BETWEEN 0 AND 1
                            ),
    evidence            JSONB NOT NULL DEFAULT '[]'::jsonb,
    reasoning_summary   TEXT,
    disagrees_with      JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_decisions_fixture
    ON audit.agent_decisions(fixture_id, created_at DESC);

CREATE TABLE IF NOT EXISTS audit.supervisor_decisions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fixture_id          UUID NOT NULL
                            REFERENCES core.fixtures(id)
                            ON DELETE CASCADE,
    prediction_id       UUID
                            REFERENCES model.predictions(id)
                            ON DELETE SET NULL,
    decision            TEXT NOT NULL CHECK (
                            decision IN (
                                'publish',
                                'delay',
                                'abstain',
                                'request_more_data'
                            )
                        ),
    confidence          NUMERIC(5,4)
                            CHECK (
                                confidence IS NULL OR
                                confidence BETWEEN 0 AND 1
                            ),
    reasons             JSONB NOT NULL DEFAULT '[]'::jsonb,
    agent_votes         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================================================
-- تقييم التوقع بعد المباراة
-- =========================================================

CREATE TABLE IF NOT EXISTS model.prediction_evaluations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_id       UUID NOT NULL UNIQUE
                            REFERENCES model.predictions(id)
                            ON DELETE CASCADE,
    evaluated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actual_home_score   SMALLINT NOT NULL,
    actual_away_score   SMALLINT NOT NULL,
    result_1x2_correct  BOOLEAN NOT NULL,
    exact_score_correct BOOLEAN NOT NULL,
    over_2_5_correct    BOOLEAN,
    both_teams_correct  BOOLEAN,
    brier_score         NUMERIC(12,10),
    log_loss            NUMERIC(12,10),
    ranked_probability_score NUMERIC(12,10),
    home_goal_error     NUMERIC(8,4),
    away_goal_error     NUMERIC(8,4),
    total_score         NUMERIC(6,3),
    exceptional_events  JSONB NOT NULL DEFAULT '[]'::jsonb,
    notes               TEXT
);

-- =========================================================
-- فرضيات البحث والتحسين
-- =========================================================

CREATE TABLE IF NOT EXISTS audit.hypotheses (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title               TEXT NOT NULL,
    description         TEXT NOT NULL,
    proposed_by         TEXT NOT NULL,
    hypothesis_status   TEXT NOT NULL DEFAULT 'proposed'
                            CHECK (
                                hypothesis_status IN (
                                    'proposed',
                                    'testing',
                                    'supported',
                                    'rejected',
                                    'inconclusive'
                                )
                            ),
    minimum_sample_size INTEGER,
    current_sample_size INTEGER NOT NULL DEFAULT 0,
    test_definition     JSONB NOT NULL DEFAULT '{}'::jsonb,
    results             JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMIT;
