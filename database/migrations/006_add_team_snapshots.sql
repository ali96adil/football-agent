CREATE TABLE IF NOT EXISTS core.team_snapshots (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    team_id uuid NOT NULL
        REFERENCES core.teams(id)
        ON DELETE CASCADE,

    competition_id uuid NOT NULL
        REFERENCES core.competitions(id)
        ON DELETE CASCADE,

    season_id uuid NOT NULL
        REFERENCES core.seasons(id)
        ON DELETE CASCADE,

    snapshot_at timestamptz NOT NULL DEFAULT now(),
    data_cutoff_at timestamptz NOT NULL DEFAULT now(),

    window_size integer NOT NULL,

    matches_played integer NOT NULL DEFAULT 0,
    wins integer NOT NULL DEFAULT 0,
    draws integer NOT NULL DEFAULT 0,
    losses integer NOT NULL DEFAULT 0,

    points integer NOT NULL DEFAULT 0,
    points_per_game numeric(8,4),

    goals_for integer NOT NULL DEFAULT 0,
    goals_against integer NOT NULL DEFAULT 0,
    goal_difference integer NOT NULL DEFAULT 0,

    goals_for_per_game numeric(8,4),
    goals_against_per_game numeric(8,4),

    clean_sheets integer NOT NULL DEFAULT 0,
    failed_to_score integer NOT NULL DEFAULT 0,
    btts_count integer NOT NULL DEFAULT 0,
    over_2_5_count integer NOT NULL DEFAULT 0,

    btts_rate numeric(8,4),
    over_2_5_rate numeric(8,4),
    clean_sheet_rate numeric(8,4),
    failed_to_score_rate numeric(8,4),

    home_matches integer NOT NULL DEFAULT 0,
    home_wins integer NOT NULL DEFAULT 0,
    home_draws integer NOT NULL DEFAULT 0,
    home_losses integer NOT NULL DEFAULT 0,
    home_points integer NOT NULL DEFAULT 0,

    home_points_per_game numeric(8,4),
    home_goals_for_per_game numeric(8,4),
    home_goals_against_per_game numeric(8,4),

    away_matches integer NOT NULL DEFAULT 0,
    away_wins integer NOT NULL DEFAULT 0,
    away_draws integer NOT NULL DEFAULT 0,
    away_losses integer NOT NULL DEFAULT 0,
    away_points integer NOT NULL DEFAULT 0,

    away_points_per_game numeric(8,4),
    away_goals_for_per_game numeric(8,4),
    away_goals_against_per_game numeric(8,4),

    current_position integer,
    current_league_points integer,

    days_since_last_match numeric(8,2),

    attack_rating numeric(10,4),
    defence_rating numeric(10,4),
    home_rating numeric(10,4),
    away_rating numeric(10,4),
    form_rating numeric(10,4),

    elo_rating numeric(10,4),

    form_sequence text,

    data_completeness numeric(5,4) NOT NULL DEFAULT 0,
    calculation_version text NOT NULL DEFAULT 'v1',
    snapshot_hash text,

    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,

    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT team_snapshots_window_size_check
        CHECK (window_size > 0),

    CONSTRAINT team_snapshots_matches_played_check
        CHECK (matches_played >= 0),

    CONSTRAINT team_snapshots_results_check
        CHECK (
            wins >= 0
            AND draws >= 0
            AND losses >= 0
            AND wins + draws + losses <= matches_played
        ),

    CONSTRAINT team_snapshots_goal_counts_check
        CHECK (
            goals_for >= 0
            AND goals_against >= 0
            AND clean_sheets >= 0
            AND failed_to_score >= 0
            AND btts_count >= 0
            AND over_2_5_count >= 0
        ),

    CONSTRAINT team_snapshots_home_results_check
        CHECK (
            home_matches >= 0
            AND home_wins >= 0
            AND home_draws >= 0
            AND home_losses >= 0
            AND home_wins + home_draws + home_losses <= home_matches
        ),

    CONSTRAINT team_snapshots_away_results_check
        CHECK (
            away_matches >= 0
            AND away_wins >= 0
            AND away_draws >= 0
            AND away_losses >= 0
            AND away_wins + away_draws + away_losses <= away_matches
        ),

    CONSTRAINT team_snapshots_data_completeness_check
        CHECK (
            data_completeness >= 0
            AND data_completeness <= 1
        ),

    CONSTRAINT team_snapshots_btts_rate_check
        CHECK (
            btts_rate IS NULL
            OR (btts_rate >= 0 AND btts_rate <= 1)
        ),

    CONSTRAINT team_snapshots_over_2_5_rate_check
        CHECK (
            over_2_5_rate IS NULL
            OR (over_2_5_rate >= 0 AND over_2_5_rate <= 1)
        ),

    CONSTRAINT team_snapshots_clean_sheet_rate_check
        CHECK (
            clean_sheet_rate IS NULL
            OR (clean_sheet_rate >= 0 AND clean_sheet_rate <= 1)
        ),

    CONSTRAINT team_snapshots_failed_to_score_rate_check
        CHECK (
            failed_to_score_rate IS NULL
            OR (failed_to_score_rate >= 0 AND failed_to_score_rate <= 1)
        )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_team_snapshots_identity
    ON core.team_snapshots (
        team_id,
        competition_id,
        season_id,
        window_size,
        snapshot_at,
        calculation_version
    );

CREATE UNIQUE INDEX IF NOT EXISTS uq_team_snapshots_hash
    ON core.team_snapshots (snapshot_hash)
    WHERE snapshot_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_team_snapshots_team_time
    ON core.team_snapshots (
        team_id,
        snapshot_at DESC
    );

CREATE INDEX IF NOT EXISTS idx_team_snapshots_competition_time
    ON core.team_snapshots (
        competition_id,
        snapshot_at DESC
    );

CREATE INDEX IF NOT EXISTS idx_team_snapshots_season
    ON core.team_snapshots (
        season_id,
        team_id
    );

CREATE INDEX IF NOT EXISTS idx_team_snapshots_window
    ON core.team_snapshots (
        window_size,
        snapshot_at DESC
    );

DROP VIEW IF EXISTS core.latest_team_snapshots;

CREATE VIEW core.latest_team_snapshots AS
SELECT DISTINCT ON (
    team_id,
    competition_id,
    season_id,
    window_size
)
    *
FROM core.team_snapshots
ORDER BY
    team_id,
    competition_id,
    season_id,
    window_size,
    snapshot_at DESC,
    created_at DESC;

COMMENT ON TABLE core.team_snapshots IS
'Historical calculated intelligence snapshots for football teams.';

COMMENT ON COLUMN core.team_snapshots.window_size IS
'Number of recent completed fixtures used for calculating the snapshot.';

COMMENT ON COLUMN core.team_snapshots.data_cutoff_at IS
'Latest point in time from which source data was allowed to be used.';

COMMENT ON COLUMN core.team_snapshots.form_sequence IS
'Recent results ordered from oldest to newest, such as WDLWW.';

COMMENT ON COLUMN core.team_snapshots.snapshot_hash IS
'Deterministic hash used to avoid duplicate snapshots with identical content.';

COMMENT ON VIEW core.latest_team_snapshots IS
'Latest team intelligence snapshot for each team, competition, season and window size.';

COMMIT;
