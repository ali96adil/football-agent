CREATE TABLE IF NOT EXISTS core.match_predictions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    fixture_id uuid
        REFERENCES core.fixtures(id)
        ON DELETE SET NULL,

    competition_id uuid NOT NULL
        REFERENCES core.competitions(id)
        ON DELETE CASCADE,

    season_id uuid NOT NULL
        REFERENCES core.seasons(id)
        ON DELETE CASCADE,

    home_team_id uuid NOT NULL
        REFERENCES core.teams(id)
        ON DELETE CASCADE,

    away_team_id uuid NOT NULL
        REFERENCES core.teams(id)
        ON DELETE CASCADE,

    home_snapshot_id uuid
        REFERENCES core.team_snapshots(id)
        ON DELETE SET NULL,

    away_snapshot_id uuid
        REFERENCES core.team_snapshots(id)
        ON DELETE SET NULL,

    predicted_at timestamptz NOT NULL DEFAULT now(),
    kickoff_at timestamptz,

    home_expected_goals numeric(10,4) NOT NULL,
    away_expected_goals numeric(10,4) NOT NULL,
    total_expected_goals numeric(10,4) NOT NULL,

    home_win_probability numeric(8,6) NOT NULL,
    draw_probability numeric(8,6) NOT NULL,
    away_win_probability numeric(8,6) NOT NULL,

    btts_yes_probability numeric(8,6) NOT NULL,
    btts_no_probability numeric(8,6) NOT NULL,

    over_2_5_probability numeric(8,6) NOT NULL,
    under_2_5_probability numeric(8,6) NOT NULL,

    predicted_outcome text NOT NULL,

    most_likely_home_goals integer,
    most_likely_away_goals integer,
    most_likely_score_probability numeric(8,6),

    confidence numeric(8,6) NOT NULL DEFAULT 0,

    expected_goals_model_version text NOT NULL,
    probability_model_version text NOT NULL,

    feature_vector jsonb NOT NULL DEFAULT '{}'::jsonb,
    most_likely_scores jsonb NOT NULL DEFAULT '[]'::jsonb,

    actual_home_goals integer,
    actual_away_goals integer,
    actual_outcome text,

    result_confirmed boolean NOT NULL DEFAULT false,
    evaluated_at timestamptz,

    outcome_correct boolean,
    exact_score_correct boolean,

    brier_score numeric(12,8),
    log_loss numeric(12,8),

    home_probability_error numeric(12,8),
    draw_probability_error numeric(12,8),
    away_probability_error numeric(12,8),

    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,

    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT match_predictions_different_teams_check
        CHECK (home_team_id <> away_team_id),

    CONSTRAINT match_predictions_expected_goals_check
        CHECK (
            home_expected_goals >= 0
            AND away_expected_goals >= 0
            AND total_expected_goals >= 0
        ),

    CONSTRAINT match_predictions_outcome_check
        CHECK (
            predicted_outcome IN (
                'home_win',
                'draw',
                'away_win'
            )
        ),

    CONSTRAINT match_predictions_actual_outcome_check
        CHECK (
            actual_outcome IS NULL
            OR actual_outcome IN (
                'home_win',
                'draw',
                'away_win'
            )
        ),

    CONSTRAINT match_predictions_probabilities_check
        CHECK (
            home_win_probability BETWEEN 0 AND 1
            AND draw_probability BETWEEN 0 AND 1
            AND away_win_probability BETWEEN 0 AND 1
            AND btts_yes_probability BETWEEN 0 AND 1
            AND btts_no_probability BETWEEN 0 AND 1
            AND over_2_5_probability BETWEEN 0 AND 1
            AND under_2_5_probability BETWEEN 0 AND 1
            AND confidence BETWEEN 0 AND 1
        ),

    CONSTRAINT match_predictions_actual_scores_check
        CHECK (
            (actual_home_goals IS NULL OR actual_home_goals >= 0)
            AND
            (actual_away_goals IS NULL OR actual_away_goals >= 0)
        ),

    CONSTRAINT match_predictions_likely_scores_check
        CHECK (
            (
                most_likely_home_goals IS NULL
                AND most_likely_away_goals IS NULL
            )
            OR
            (
                most_likely_home_goals >= 0
                AND most_likely_away_goals >= 0
            )
        )
);

CREATE INDEX IF NOT EXISTS idx_match_predictions_fixture
    ON core.match_predictions (fixture_id);

CREATE INDEX IF NOT EXISTS idx_match_predictions_competition_season
    ON core.match_predictions (
        competition_id,
        season_id,
        predicted_at DESC
    );

CREATE INDEX IF NOT EXISTS idx_match_predictions_teams
    ON core.match_predictions (
        home_team_id,
        away_team_id,
        predicted_at DESC
    );

CREATE INDEX IF NOT EXISTS idx_match_predictions_pending_evaluation
    ON core.match_predictions (
        result_confirmed,
        kickoff_at
    )
    WHERE result_confirmed = false;

CREATE INDEX IF NOT EXISTS idx_match_predictions_model_versions
    ON core.match_predictions (
        expected_goals_model_version,
        probability_model_version,
        predicted_at DESC
    );

CREATE UNIQUE INDEX IF NOT EXISTS uq_match_predictions_fixture_models
    ON core.match_predictions (
        fixture_id,
        expected_goals_model_version,
        probability_model_version
    )
    WHERE fixture_id IS NOT NULL;

COMMENT ON TABLE core.match_predictions IS
    'Stores pre-match model predictions and their later evaluation against actual fixture results.';

COMMENT ON COLUMN core.match_predictions.brier_score IS
    'Multiclass Brier score for home win, draw and away win probabilities. Lower is better.';

COMMENT ON COLUMN core.match_predictions.log_loss IS
    'Negative logarithm of the probability assigned to the actual outcome. Lower is better.';
