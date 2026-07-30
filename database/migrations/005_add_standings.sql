CREATE TABLE IF NOT EXISTS core.standing_snapshots (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    competition_id uuid NOT NULL
        REFERENCES core.competitions(id)
        ON DELETE CASCADE,

    season_id uuid
        REFERENCES core.seasons(id)
        ON DELETE SET NULL,

    source_id bigint NOT NULL
        REFERENCES core.data_sources(id)
        ON DELETE CASCADE,

    raw_payload_id bigint
        REFERENCES raw.api_payloads(id)
        ON DELETE SET NULL,

    competition_code text NOT NULL,

    standing_type text NOT NULL DEFAULT 'TOTAL',

    snapshot_at timestamp with time zone NOT NULL DEFAULT now(),

    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,

    created_at timestamp with time zone NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_standing_snapshots_competition
    ON core.standing_snapshots (
        competition_id,
        snapshot_at DESC
    );

CREATE INDEX IF NOT EXISTS idx_standing_snapshots_season
    ON core.standing_snapshots (
        season_id,
        snapshot_at DESC
    );

CREATE INDEX IF NOT EXISTS idx_standing_snapshots_raw_payload
    ON core.standing_snapshots (raw_payload_id);


CREATE TABLE IF NOT EXISTS core.standing_rows (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    snapshot_id uuid NOT NULL
        REFERENCES core.standing_snapshots(id)
        ON DELETE CASCADE,

    team_id uuid NOT NULL
        REFERENCES core.teams(id)
        ON DELETE CASCADE,

    position integer NOT NULL,

    played_games integer NOT NULL DEFAULT 0,

    won integer NOT NULL DEFAULT 0,

    draw integer NOT NULL DEFAULT 0,

    lost integer NOT NULL DEFAULT 0,

    points integer NOT NULL DEFAULT 0,

    goals_for integer NOT NULL DEFAULT 0,

    goals_against integer NOT NULL DEFAULT 0,

    goal_difference integer NOT NULL DEFAULT 0,

    form text,

    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,

    created_at timestamp with time zone NOT NULL DEFAULT now(),

    CONSTRAINT standing_rows_snapshot_team_unique
        UNIQUE (snapshot_id, team_id),

    CONSTRAINT standing_rows_snapshot_position_unique
        UNIQUE (snapshot_id, position),

    CONSTRAINT standing_rows_position_check
        CHECK (position > 0),

    CONSTRAINT standing_rows_played_games_check
        CHECK (played_games >= 0),

    CONSTRAINT standing_rows_won_check
        CHECK (won >= 0),

    CONSTRAINT standing_rows_draw_check
        CHECK (draw >= 0),

    CONSTRAINT standing_rows_lost_check
        CHECK (lost >= 0),

    CONSTRAINT standing_rows_points_check
        CHECK (points >= 0),

    CONSTRAINT standing_rows_match_totals_check
        CHECK (won + draw + lost <= played_games)
);

CREATE INDEX IF NOT EXISTS idx_standing_rows_snapshot
    ON core.standing_rows (
        snapshot_id,
        position
    );

CREATE INDEX IF NOT EXISTS idx_standing_rows_team
    ON core.standing_rows (
        team_id,
        created_at DESC
    );
