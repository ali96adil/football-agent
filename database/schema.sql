--
-- PostgreSQL database dump
--

\restrict vT9OyDk4OROIxTGFz2xlNyeTB9jhluwAk3ONoSJAxCsMEec0WM9fiMFIZUcZ1ld

-- Dumped from database version 17.10
-- Dumped by pg_dump version 17.10

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: audit; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA audit;


--
-- Name: core; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA core;


--
-- Name: model; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA model;


--
-- Name: raw; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA raw;


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agent_decisions; Type: TABLE; Schema: audit; Owner: -
--

CREATE TABLE audit.agent_decisions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    fixture_id uuid,
    prediction_id uuid,
    agent_name text NOT NULL,
    agent_version text NOT NULL,
    decision_type text NOT NULL,
    decision text NOT NULL,
    confidence numeric(5,4),
    evidence jsonb DEFAULT '[]'::jsonb NOT NULL,
    reasoning_summary text,
    disagrees_with jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT agent_decisions_confidence_check CHECK (((confidence IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))))
);


--
-- Name: hypotheses; Type: TABLE; Schema: audit; Owner: -
--

CREATE TABLE audit.hypotheses (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    proposed_by text NOT NULL,
    hypothesis_status text DEFAULT 'proposed'::text NOT NULL,
    minimum_sample_size integer,
    current_sample_size integer DEFAULT 0 NOT NULL,
    test_definition jsonb DEFAULT '{}'::jsonb NOT NULL,
    results jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT hypotheses_hypothesis_status_check CHECK ((hypothesis_status = ANY (ARRAY['proposed'::text, 'testing'::text, 'supported'::text, 'rejected'::text, 'inconclusive'::text])))
);


--
-- Name: supervisor_decisions; Type: TABLE; Schema: audit; Owner: -
--

CREATE TABLE audit.supervisor_decisions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    fixture_id uuid NOT NULL,
    prediction_id uuid,
    decision text NOT NULL,
    confidence numeric(5,4),
    reasons jsonb DEFAULT '[]'::jsonb NOT NULL,
    agent_votes jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT supervisor_decisions_confidence_check CHECK (((confidence IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric)))),
    CONSTRAINT supervisor_decisions_decision_check CHECK ((decision = ANY (ARRAY['publish'::text, 'delay'::text, 'abstain'::text, 'request_more_data'::text])))
);


--
-- Name: competitions; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.competitions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    canonical_name text NOT NULL,
    country_code text,
    competition_type text,
    gender text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: data_sources; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.data_sources (
    id bigint NOT NULL,
    code text NOT NULL,
    name text NOT NULL,
    source_type text NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    priority smallint DEFAULT 50 NOT NULL,
    reliability_score numeric(5,4),
    daily_request_limit integer,
    reserved_requests integer DEFAULT 0 NOT NULL,
    requests_used_today integer DEFAULT 0 NOT NULL,
    last_success_at timestamp with time zone,
    last_failure_at timestamp with time zone,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT data_sources_priority_check CHECK (((priority >= 0) AND (priority <= 100))),
    CONSTRAINT data_sources_reliability_score_check CHECK (((reliability_score IS NULL) OR ((reliability_score >= (0)::numeric) AND (reliability_score <= (1)::numeric)))),
    CONSTRAINT data_sources_source_type_check CHECK ((source_type = ANY (ARRAY['api'::text, 'official_site'::text, 'news'::text, 'scraper'::text, 'weather'::text, 'market'::text, 'manual'::text])))
);


--
-- Name: data_sources_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

CREATE SEQUENCE core.data_sources_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: data_sources_id_seq; Type: SEQUENCE OWNED BY; Schema: core; Owner: -
--

ALTER SEQUENCE core.data_sources_id_seq OWNED BY core.data_sources.id;


--
-- Name: fixture_source_ids; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.fixture_source_ids (
    id bigint NOT NULL,
    fixture_id uuid NOT NULL,
    source_id bigint NOT NULL,
    external_fixture_id text NOT NULL,
    source_status text,
    source_kickoff_at timestamp with time zone,
    last_synced_at timestamp with time zone DEFAULT now() NOT NULL,
    payload_hash text
);


--
-- Name: fixture_source_ids_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

CREATE SEQUENCE core.fixture_source_ids_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: fixture_source_ids_id_seq; Type: SEQUENCE OWNED BY; Schema: core; Owner: -
--

ALTER SEQUENCE core.fixture_source_ids_id_seq OWNED BY core.fixture_source_ids.id;


--
-- Name: fixtures; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.fixtures (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    competition_id uuid,
    season_id uuid,
    home_team_id uuid NOT NULL,
    away_team_id uuid NOT NULL,
    kickoff_at timestamp with time zone NOT NULL,
    venue_name text,
    venue_city text,
    neutral_venue boolean DEFAULT false NOT NULL,
    fixture_status text DEFAULT 'scheduled'::text NOT NULL,
    home_score smallint,
    away_score smallint,
    extra_time_home smallint,
    extra_time_away smallint,
    penalties_home smallint,
    penalties_away smallint,
    winner_team_id uuid,
    result_confirmed boolean DEFAULT false NOT NULL,
    selection_score numeric(6,3),
    data_completeness numeric(5,4),
    source_quality numeric(5,4),
    selected_for_analysis boolean DEFAULT false NOT NULL,
    selection_rank smallint,
    rejection_reason text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT fixtures_check CHECK ((home_team_id <> away_team_id)),
    CONSTRAINT fixtures_data_completeness_check CHECK (((data_completeness IS NULL) OR ((data_completeness >= (0)::numeric) AND (data_completeness <= (1)::numeric)))),
    CONSTRAINT fixtures_source_quality_check CHECK (((source_quality IS NULL) OR ((source_quality >= (0)::numeric) AND (source_quality <= (1)::numeric))))
);


--
-- Name: team_snapshots; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.team_snapshots (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    team_id uuid NOT NULL,
    competition_id uuid NOT NULL,
    season_id uuid NOT NULL,
    snapshot_at timestamp with time zone DEFAULT now() NOT NULL,
    data_cutoff_at timestamp with time zone DEFAULT now() NOT NULL,
    window_size integer NOT NULL,
    matches_played integer DEFAULT 0 NOT NULL,
    wins integer DEFAULT 0 NOT NULL,
    draws integer DEFAULT 0 NOT NULL,
    losses integer DEFAULT 0 NOT NULL,
    points integer DEFAULT 0 NOT NULL,
    points_per_game numeric(8,4),
    goals_for integer DEFAULT 0 NOT NULL,
    goals_against integer DEFAULT 0 NOT NULL,
    goal_difference integer DEFAULT 0 NOT NULL,
    goals_for_per_game numeric(8,4),
    goals_against_per_game numeric(8,4),
    clean_sheets integer DEFAULT 0 NOT NULL,
    failed_to_score integer DEFAULT 0 NOT NULL,
    btts_count integer DEFAULT 0 NOT NULL,
    over_2_5_count integer DEFAULT 0 NOT NULL,
    btts_rate numeric(8,4),
    over_2_5_rate numeric(8,4),
    clean_sheet_rate numeric(8,4),
    failed_to_score_rate numeric(8,4),
    home_matches integer DEFAULT 0 NOT NULL,
    home_wins integer DEFAULT 0 NOT NULL,
    home_draws integer DEFAULT 0 NOT NULL,
    home_losses integer DEFAULT 0 NOT NULL,
    home_points integer DEFAULT 0 NOT NULL,
    home_points_per_game numeric(8,4),
    home_goals_for_per_game numeric(8,4),
    home_goals_against_per_game numeric(8,4),
    away_matches integer DEFAULT 0 NOT NULL,
    away_wins integer DEFAULT 0 NOT NULL,
    away_draws integer DEFAULT 0 NOT NULL,
    away_losses integer DEFAULT 0 NOT NULL,
    away_points integer DEFAULT 0 NOT NULL,
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
    data_completeness numeric(5,4) DEFAULT 0 NOT NULL,
    calculation_version text DEFAULT 'v1'::text NOT NULL,
    snapshot_hash text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    overall_rating numeric(10,4),
    CONSTRAINT team_snapshots_away_results_check CHECK (((away_matches >= 0) AND (away_wins >= 0) AND (away_draws >= 0) AND (away_losses >= 0) AND (((away_wins + away_draws) + away_losses) <= away_matches))),
    CONSTRAINT team_snapshots_btts_rate_check CHECK (((btts_rate IS NULL) OR ((btts_rate >= (0)::numeric) AND (btts_rate <= (1)::numeric)))),
    CONSTRAINT team_snapshots_clean_sheet_rate_check CHECK (((clean_sheet_rate IS NULL) OR ((clean_sheet_rate >= (0)::numeric) AND (clean_sheet_rate <= (1)::numeric)))),
    CONSTRAINT team_snapshots_data_completeness_check CHECK (((data_completeness >= (0)::numeric) AND (data_completeness <= (1)::numeric))),
    CONSTRAINT team_snapshots_failed_to_score_rate_check CHECK (((failed_to_score_rate IS NULL) OR ((failed_to_score_rate >= (0)::numeric) AND (failed_to_score_rate <= (1)::numeric)))),
    CONSTRAINT team_snapshots_goal_counts_check CHECK (((goals_for >= 0) AND (goals_against >= 0) AND (clean_sheets >= 0) AND (failed_to_score >= 0) AND (btts_count >= 0) AND (over_2_5_count >= 0))),
    CONSTRAINT team_snapshots_home_results_check CHECK (((home_matches >= 0) AND (home_wins >= 0) AND (home_draws >= 0) AND (home_losses >= 0) AND (((home_wins + home_draws) + home_losses) <= home_matches))),
    CONSTRAINT team_snapshots_matches_played_check CHECK ((matches_played >= 0)),
    CONSTRAINT team_snapshots_over_2_5_rate_check CHECK (((over_2_5_rate IS NULL) OR ((over_2_5_rate >= (0)::numeric) AND (over_2_5_rate <= (1)::numeric)))),
    CONSTRAINT team_snapshots_results_check CHECK (((wins >= 0) AND (draws >= 0) AND (losses >= 0) AND (((wins + draws) + losses) <= matches_played))),
    CONSTRAINT team_snapshots_window_size_check CHECK ((window_size > 0))
);


--
-- Name: TABLE team_snapshots; Type: COMMENT; Schema: core; Owner: -
--

COMMENT ON TABLE core.team_snapshots IS 'Historical calculated intelligence snapshots for football teams.';


--
-- Name: COLUMN team_snapshots.data_cutoff_at; Type: COMMENT; Schema: core; Owner: -
--

COMMENT ON COLUMN core.team_snapshots.data_cutoff_at IS 'Latest point in time from which source data was allowed to be used.';


--
-- Name: COLUMN team_snapshots.window_size; Type: COMMENT; Schema: core; Owner: -
--

COMMENT ON COLUMN core.team_snapshots.window_size IS 'Number of recent completed fixtures used for calculating the snapshot.';


--
-- Name: COLUMN team_snapshots.form_sequence; Type: COMMENT; Schema: core; Owner: -
--

COMMENT ON COLUMN core.team_snapshots.form_sequence IS 'Recent results ordered from oldest to newest, such as WDLWW.';


--
-- Name: COLUMN team_snapshots.snapshot_hash; Type: COMMENT; Schema: core; Owner: -
--

COMMENT ON COLUMN core.team_snapshots.snapshot_hash IS 'Deterministic hash used to avoid duplicate snapshots with identical content.';


--
-- Name: COLUMN team_snapshots.overall_rating; Type: COMMENT; Schema: core; Owner: -
--

COMMENT ON COLUMN core.team_snapshots.overall_rating IS 'Overall composite rating calculated from attack, defence, home, away and form ratings.';


--
-- Name: latest_team_snapshots; Type: VIEW; Schema: core; Owner: -
--

CREATE VIEW core.latest_team_snapshots AS
 SELECT DISTINCT ON (team_id, competition_id, season_id, window_size) id,
    team_id,
    competition_id,
    season_id,
    snapshot_at,
    data_cutoff_at,
    window_size,
    matches_played,
    wins,
    draws,
    losses,
    points,
    points_per_game,
    goals_for,
    goals_against,
    goal_difference,
    goals_for_per_game,
    goals_against_per_game,
    clean_sheets,
    failed_to_score,
    btts_count,
    over_2_5_count,
    btts_rate,
    over_2_5_rate,
    clean_sheet_rate,
    failed_to_score_rate,
    home_matches,
    home_wins,
    home_draws,
    home_losses,
    home_points,
    home_points_per_game,
    home_goals_for_per_game,
    home_goals_against_per_game,
    away_matches,
    away_wins,
    away_draws,
    away_losses,
    away_points,
    away_points_per_game,
    away_goals_for_per_game,
    away_goals_against_per_game,
    current_position,
    current_league_points,
    days_since_last_match,
    attack_rating,
    defence_rating,
    home_rating,
    away_rating,
    form_rating,
    elo_rating,
    form_sequence,
    data_completeness,
    calculation_version,
    snapshot_hash,
    metadata,
    created_at
   FROM core.team_snapshots
  ORDER BY team_id, competition_id, season_id, window_size, snapshot_at DESC, created_at DESC;


--
-- Name: VIEW latest_team_snapshots; Type: COMMENT; Schema: core; Owner: -
--

COMMENT ON VIEW core.latest_team_snapshots IS 'Latest team intelligence snapshot for each team, competition, season and window size.';


--
-- Name: match_predictions; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.match_predictions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    fixture_id uuid,
    competition_id uuid NOT NULL,
    season_id uuid NOT NULL,
    home_team_id uuid NOT NULL,
    away_team_id uuid NOT NULL,
    home_snapshot_id uuid,
    away_snapshot_id uuid,
    predicted_at timestamp with time zone DEFAULT now() NOT NULL,
    kickoff_at timestamp with time zone,
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
    confidence numeric(8,6) DEFAULT 0 NOT NULL,
    expected_goals_model_version text NOT NULL,
    probability_model_version text NOT NULL,
    feature_vector jsonb DEFAULT '{}'::jsonb NOT NULL,
    most_likely_scores jsonb DEFAULT '[]'::jsonb NOT NULL,
    actual_home_goals integer,
    actual_away_goals integer,
    actual_outcome text,
    result_confirmed boolean DEFAULT false NOT NULL,
    evaluated_at timestamp with time zone,
    outcome_correct boolean,
    exact_score_correct boolean,
    brier_score numeric(12,8),
    log_loss numeric(12,8),
    home_probability_error numeric(12,8),
    draw_probability_error numeric(12,8),
    away_probability_error numeric(12,8),
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT match_predictions_actual_outcome_check CHECK (((actual_outcome IS NULL) OR (actual_outcome = ANY (ARRAY['home_win'::text, 'draw'::text, 'away_win'::text])))),
    CONSTRAINT match_predictions_actual_scores_check CHECK ((((actual_home_goals IS NULL) OR (actual_home_goals >= 0)) AND ((actual_away_goals IS NULL) OR (actual_away_goals >= 0)))),
    CONSTRAINT match_predictions_different_teams_check CHECK ((home_team_id <> away_team_id)),
    CONSTRAINT match_predictions_expected_goals_check CHECK (((home_expected_goals >= (0)::numeric) AND (away_expected_goals >= (0)::numeric) AND (total_expected_goals >= (0)::numeric))),
    CONSTRAINT match_predictions_likely_scores_check CHECK ((((most_likely_home_goals IS NULL) AND (most_likely_away_goals IS NULL)) OR ((most_likely_home_goals >= 0) AND (most_likely_away_goals >= 0)))),
    CONSTRAINT match_predictions_outcome_check CHECK ((predicted_outcome = ANY (ARRAY['home_win'::text, 'draw'::text, 'away_win'::text]))),
    CONSTRAINT match_predictions_probabilities_check CHECK ((((home_win_probability >= (0)::numeric) AND (home_win_probability <= (1)::numeric)) AND ((draw_probability >= (0)::numeric) AND (draw_probability <= (1)::numeric)) AND ((away_win_probability >= (0)::numeric) AND (away_win_probability <= (1)::numeric)) AND ((btts_yes_probability >= (0)::numeric) AND (btts_yes_probability <= (1)::numeric)) AND ((btts_no_probability >= (0)::numeric) AND (btts_no_probability <= (1)::numeric)) AND ((over_2_5_probability >= (0)::numeric) AND (over_2_5_probability <= (1)::numeric)) AND ((under_2_5_probability >= (0)::numeric) AND (under_2_5_probability <= (1)::numeric)) AND ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))))
);


--
-- Name: TABLE match_predictions; Type: COMMENT; Schema: core; Owner: -
--

COMMENT ON TABLE core.match_predictions IS 'Stores pre-match model predictions and their later evaluation against actual fixture results.';


--
-- Name: COLUMN match_predictions.brier_score; Type: COMMENT; Schema: core; Owner: -
--

COMMENT ON COLUMN core.match_predictions.brier_score IS 'Multiclass Brier score for home win, draw and away win probabilities. Lower is better.';


--
-- Name: COLUMN match_predictions.log_loss; Type: COMMENT; Schema: core; Owner: -
--

COMMENT ON COLUMN core.match_predictions.log_loss IS 'Negative logarithm of the probability assigned to the actual outcome. Lower is better.';


--
-- Name: seasons; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.seasons (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    competition_id uuid NOT NULL,
    label text NOT NULL,
    starts_on date,
    ends_on date,
    is_current boolean DEFAULT false NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: standing_rows; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.standing_rows (
    id bigint NOT NULL,
    snapshot_id uuid NOT NULL,
    team_id uuid NOT NULL,
    "position" integer NOT NULL,
    played_games integer DEFAULT 0 NOT NULL,
    won integer DEFAULT 0 NOT NULL,
    draw integer DEFAULT 0 NOT NULL,
    lost integer DEFAULT 0 NOT NULL,
    points integer DEFAULT 0 NOT NULL,
    goals_for integer DEFAULT 0 NOT NULL,
    goals_against integer DEFAULT 0 NOT NULL,
    goal_difference integer DEFAULT 0 NOT NULL,
    form text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT standing_rows_draw_check CHECK ((draw >= 0)),
    CONSTRAINT standing_rows_lost_check CHECK ((lost >= 0)),
    CONSTRAINT standing_rows_match_totals_check CHECK ((((won + draw) + lost) <= played_games)),
    CONSTRAINT standing_rows_played_games_check CHECK ((played_games >= 0)),
    CONSTRAINT standing_rows_points_check CHECK ((points >= 0)),
    CONSTRAINT standing_rows_position_check CHECK (("position" > 0)),
    CONSTRAINT standing_rows_won_check CHECK ((won >= 0))
);


--
-- Name: standing_rows_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

ALTER TABLE core.standing_rows ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME core.standing_rows_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: standing_snapshots; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.standing_snapshots (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    competition_id uuid NOT NULL,
    season_id uuid,
    source_id bigint NOT NULL,
    raw_payload_id bigint,
    competition_code text NOT NULL,
    standing_type text DEFAULT 'TOTAL'::text NOT NULL,
    snapshot_at timestamp with time zone DEFAULT now() NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: team_aliases; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.team_aliases (
    id bigint NOT NULL,
    team_id uuid NOT NULL,
    alias text NOT NULL,
    language_code text,
    source_id bigint,
    normalized_alias text NOT NULL
);


--
-- Name: team_aliases_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

CREATE SEQUENCE core.team_aliases_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: team_aliases_id_seq; Type: SEQUENCE OWNED BY; Schema: core; Owner: -
--

ALTER SEQUENCE core.team_aliases_id_seq OWNED BY core.team_aliases.id;


--
-- Name: team_source_ids; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.team_source_ids (
    id bigint NOT NULL,
    team_id uuid NOT NULL,
    source_id bigint NOT NULL,
    external_team_id text NOT NULL,
    source_name text,
    confidence numeric(5,4) DEFAULT 1 NOT NULL,
    verified boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT team_source_ids_confidence_check CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric)))
);


--
-- Name: team_source_ids_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

CREATE SEQUENCE core.team_source_ids_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: team_source_ids_id_seq; Type: SEQUENCE OWNED BY; Schema: core; Owner: -
--

ALTER SEQUENCE core.team_source_ids_id_seq OWNED BY core.team_source_ids.id;


--
-- Name: teams; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.teams (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    canonical_name text NOT NULL,
    short_name text,
    country_code text,
    founded_year integer,
    logo_url text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: feature_snapshots; Type: TABLE; Schema: model; Owner: -
--

CREATE TABLE model.feature_snapshots (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    fixture_id uuid NOT NULL,
    snapshot_type text NOT NULL,
    captured_at timestamp with time zone DEFAULT now() NOT NULL,
    data_cutoff_at timestamp with time zone NOT NULL,
    feature_version text NOT NULL,
    data_completeness numeric(5,4) NOT NULL,
    source_quality numeric(5,4) NOT NULL,
    source_agreement numeric(5,4),
    features jsonb NOT NULL,
    feature_hash text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT feature_snapshots_data_completeness_check CHECK (((data_completeness >= (0)::numeric) AND (data_completeness <= (1)::numeric))),
    CONSTRAINT feature_snapshots_snapshot_type_check CHECK ((snapshot_type = ANY (ARRAY['discovery'::text, 'early'::text, 'prematch'::text, 'lineup'::text, 'postmatch'::text]))),
    CONSTRAINT feature_snapshots_source_agreement_check CHECK (((source_agreement IS NULL) OR ((source_agreement >= (0)::numeric) AND (source_agreement <= (1)::numeric)))),
    CONSTRAINT feature_snapshots_source_quality_check CHECK (((source_quality >= (0)::numeric) AND (source_quality <= (1)::numeric)))
);


--
-- Name: model_versions; Type: TABLE; Schema: model; Owner: -
--

CREATE TABLE model.model_versions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    model_name text NOT NULL,
    version text NOT NULL,
    model_family text NOT NULL,
    status text DEFAULT 'candidate'::text NOT NULL,
    training_started_at timestamp with time zone,
    training_ended_at timestamp with time zone,
    training_matches integer,
    validation_matches integer,
    test_matches integer,
    metrics jsonb DEFAULT '{}'::jsonb NOT NULL,
    configuration jsonb DEFAULT '{}'::jsonb NOT NULL,
    artifact_path text,
    parent_version_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT model_versions_status_check CHECK ((status = ANY (ARRAY['candidate'::text, 'active'::text, 'retired'::text, 'rejected'::text])))
);


--
-- Name: model_weights; Type: TABLE; Schema: model; Owner: -
--

CREATE TABLE model.model_weights (
    id bigint NOT NULL,
    model_version_id uuid NOT NULL,
    prediction_target text NOT NULL,
    component_name text NOT NULL,
    weight_value numeric(12,8) NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: model_weights_id_seq; Type: SEQUENCE; Schema: model; Owner: -
--

CREATE SEQUENCE model.model_weights_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: model_weights_id_seq; Type: SEQUENCE OWNED BY; Schema: model; Owner: -
--

ALTER SEQUENCE model.model_weights_id_seq OWNED BY model.model_weights.id;


--
-- Name: prediction_evaluations; Type: TABLE; Schema: model; Owner: -
--

CREATE TABLE model.prediction_evaluations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    prediction_id uuid NOT NULL,
    evaluated_at timestamp with time zone DEFAULT now() NOT NULL,
    actual_home_score smallint NOT NULL,
    actual_away_score smallint NOT NULL,
    result_1x2_correct boolean NOT NULL,
    exact_score_correct boolean NOT NULL,
    over_2_5_correct boolean,
    both_teams_correct boolean,
    brier_score numeric(12,10),
    log_loss numeric(12,10),
    ranked_probability_score numeric(12,10),
    home_goal_error numeric(8,4),
    away_goal_error numeric(8,4),
    total_score numeric(6,3),
    exceptional_events jsonb DEFAULT '[]'::jsonb NOT NULL,
    notes text
);


--
-- Name: predictions; Type: TABLE; Schema: model; Owner: -
--

CREATE TABLE model.predictions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    fixture_id uuid NOT NULL,
    feature_snapshot_id uuid NOT NULL,
    model_version_id uuid,
    prediction_stage text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    home_win_probability numeric(7,6) NOT NULL,
    draw_probability numeric(7,6) NOT NULL,
    away_win_probability numeric(7,6) NOT NULL,
    expected_home_goals numeric(7,4),
    expected_away_goals numeric(7,4),
    predicted_home_score smallint,
    predicted_away_score smallint,
    over_2_5_probability numeric(7,6),
    both_teams_score_probability numeric(7,6),
    calibrated_confidence numeric(5,4),
    publish_decision boolean DEFAULT false NOT NULL,
    abstention_reason text,
    explanation jsonb DEFAULT '{}'::jsonb NOT NULL,
    raw_model_output jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT predictions_calibrated_confidence_check CHECK (((calibrated_confidence IS NULL) OR ((calibrated_confidence >= (0)::numeric) AND (calibrated_confidence <= (1)::numeric)))),
    CONSTRAINT predictions_check CHECK ((abs((((home_win_probability + draw_probability) + away_win_probability) - (1)::numeric)) < 0.001)),
    CONSTRAINT predictions_prediction_stage_check CHECK ((prediction_stage = ANY (ARRAY['early'::text, 'prematch'::text, 'lineup'::text])))
);


--
-- Name: api_payloads; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.api_payloads (
    id bigint NOT NULL,
    source_id bigint NOT NULL,
    fixture_id uuid,
    endpoint text NOT NULL,
    request_key text,
    requested_at timestamp with time zone DEFAULT now() NOT NULL,
    response_status integer,
    payload jsonb,
    payload_hash text,
    expires_at timestamp with time zone,
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: api_payloads_id_seq; Type: SEQUENCE; Schema: raw; Owner: -
--

CREATE SEQUENCE raw.api_payloads_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: api_payloads_id_seq; Type: SEQUENCE OWNED BY; Schema: raw; Owner: -
--

ALTER SEQUENCE raw.api_payloads_id_seq OWNED BY raw.api_payloads.id;


--
-- Name: data_sources id; Type: DEFAULT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.data_sources ALTER COLUMN id SET DEFAULT nextval('core.data_sources_id_seq'::regclass);


--
-- Name: fixture_source_ids id; Type: DEFAULT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.fixture_source_ids ALTER COLUMN id SET DEFAULT nextval('core.fixture_source_ids_id_seq'::regclass);


--
-- Name: team_aliases id; Type: DEFAULT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.team_aliases ALTER COLUMN id SET DEFAULT nextval('core.team_aliases_id_seq'::regclass);


--
-- Name: team_source_ids id; Type: DEFAULT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.team_source_ids ALTER COLUMN id SET DEFAULT nextval('core.team_source_ids_id_seq'::regclass);


--
-- Name: model_weights id; Type: DEFAULT; Schema: model; Owner: -
--

ALTER TABLE ONLY model.model_weights ALTER COLUMN id SET DEFAULT nextval('model.model_weights_id_seq'::regclass);


--
-- Name: api_payloads id; Type: DEFAULT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.api_payloads ALTER COLUMN id SET DEFAULT nextval('raw.api_payloads_id_seq'::regclass);


--
-- Name: agent_decisions agent_decisions_pkey; Type: CONSTRAINT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.agent_decisions
    ADD CONSTRAINT agent_decisions_pkey PRIMARY KEY (id);


--
-- Name: hypotheses hypotheses_pkey; Type: CONSTRAINT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.hypotheses
    ADD CONSTRAINT hypotheses_pkey PRIMARY KEY (id);


--
-- Name: supervisor_decisions supervisor_decisions_pkey; Type: CONSTRAINT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.supervisor_decisions
    ADD CONSTRAINT supervisor_decisions_pkey PRIMARY KEY (id);


--
-- Name: competitions competitions_canonical_name_country_code_key; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.competitions
    ADD CONSTRAINT competitions_canonical_name_country_code_key UNIQUE (canonical_name, country_code);


--
-- Name: competitions competitions_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.competitions
    ADD CONSTRAINT competitions_pkey PRIMARY KEY (id);


--
-- Name: data_sources data_sources_code_key; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.data_sources
    ADD CONSTRAINT data_sources_code_key UNIQUE (code);


--
-- Name: data_sources data_sources_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.data_sources
    ADD CONSTRAINT data_sources_pkey PRIMARY KEY (id);


--
-- Name: fixture_source_ids fixture_source_ids_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.fixture_source_ids
    ADD CONSTRAINT fixture_source_ids_pkey PRIMARY KEY (id);


--
-- Name: fixture_source_ids fixture_source_ids_source_id_external_fixture_id_key; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.fixture_source_ids
    ADD CONSTRAINT fixture_source_ids_source_id_external_fixture_id_key UNIQUE (source_id, external_fixture_id);


--
-- Name: fixtures fixtures_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.fixtures
    ADD CONSTRAINT fixtures_pkey PRIMARY KEY (id);


--
-- Name: fixtures fixtures_unique_match; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.fixtures
    ADD CONSTRAINT fixtures_unique_match UNIQUE (competition_id, kickoff_at, home_team_id, away_team_id);


--
-- Name: match_predictions match_predictions_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.match_predictions
    ADD CONSTRAINT match_predictions_pkey PRIMARY KEY (id);


--
-- Name: seasons seasons_competition_id_label_key; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.seasons
    ADD CONSTRAINT seasons_competition_id_label_key UNIQUE (competition_id, label);


--
-- Name: seasons seasons_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.seasons
    ADD CONSTRAINT seasons_pkey PRIMARY KEY (id);


--
-- Name: standing_rows standing_rows_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.standing_rows
    ADD CONSTRAINT standing_rows_pkey PRIMARY KEY (id);


--
-- Name: standing_rows standing_rows_snapshot_position_unique; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.standing_rows
    ADD CONSTRAINT standing_rows_snapshot_position_unique UNIQUE (snapshot_id, "position");


--
-- Name: standing_rows standing_rows_snapshot_team_unique; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.standing_rows
    ADD CONSTRAINT standing_rows_snapshot_team_unique UNIQUE (snapshot_id, team_id);


--
-- Name: standing_snapshots standing_snapshots_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.standing_snapshots
    ADD CONSTRAINT standing_snapshots_pkey PRIMARY KEY (id);


--
-- Name: team_aliases team_aliases_normalized_alias_team_id_key; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.team_aliases
    ADD CONSTRAINT team_aliases_normalized_alias_team_id_key UNIQUE (normalized_alias, team_id);


--
-- Name: team_aliases team_aliases_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.team_aliases
    ADD CONSTRAINT team_aliases_pkey PRIMARY KEY (id);


--
-- Name: team_snapshots team_snapshots_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.team_snapshots
    ADD CONSTRAINT team_snapshots_pkey PRIMARY KEY (id);


--
-- Name: team_source_ids team_source_ids_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.team_source_ids
    ADD CONSTRAINT team_source_ids_pkey PRIMARY KEY (id);


--
-- Name: team_source_ids team_source_ids_source_id_external_team_id_key; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.team_source_ids
    ADD CONSTRAINT team_source_ids_source_id_external_team_id_key UNIQUE (source_id, external_team_id);


--
-- Name: teams teams_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.teams
    ADD CONSTRAINT teams_pkey PRIMARY KEY (id);


--
-- Name: feature_snapshots feature_snapshots_fixture_id_snapshot_type_feature_hash_key; Type: CONSTRAINT; Schema: model; Owner: -
--

ALTER TABLE ONLY model.feature_snapshots
    ADD CONSTRAINT feature_snapshots_fixture_id_snapshot_type_feature_hash_key UNIQUE (fixture_id, snapshot_type, feature_hash);


--
-- Name: feature_snapshots feature_snapshots_pkey; Type: CONSTRAINT; Schema: model; Owner: -
--

ALTER TABLE ONLY model.feature_snapshots
    ADD CONSTRAINT feature_snapshots_pkey PRIMARY KEY (id);


--
-- Name: model_versions model_versions_model_name_version_key; Type: CONSTRAINT; Schema: model; Owner: -
--

ALTER TABLE ONLY model.model_versions
    ADD CONSTRAINT model_versions_model_name_version_key UNIQUE (model_name, version);


--
-- Name: model_versions model_versions_pkey; Type: CONSTRAINT; Schema: model; Owner: -
--

ALTER TABLE ONLY model.model_versions
    ADD CONSTRAINT model_versions_pkey PRIMARY KEY (id);


--
-- Name: model_weights model_weights_model_version_id_prediction_target_component__key; Type: CONSTRAINT; Schema: model; Owner: -
--

ALTER TABLE ONLY model.model_weights
    ADD CONSTRAINT model_weights_model_version_id_prediction_target_component__key UNIQUE (model_version_id, prediction_target, component_name);


--
-- Name: model_weights model_weights_pkey; Type: CONSTRAINT; Schema: model; Owner: -
--

ALTER TABLE ONLY model.model_weights
    ADD CONSTRAINT model_weights_pkey PRIMARY KEY (id);


--
-- Name: prediction_evaluations prediction_evaluations_pkey; Type: CONSTRAINT; Schema: model; Owner: -
--

ALTER TABLE ONLY model.prediction_evaluations
    ADD CONSTRAINT prediction_evaluations_pkey PRIMARY KEY (id);


--
-- Name: prediction_evaluations prediction_evaluations_prediction_id_key; Type: CONSTRAINT; Schema: model; Owner: -
--

ALTER TABLE ONLY model.prediction_evaluations
    ADD CONSTRAINT prediction_evaluations_prediction_id_key UNIQUE (prediction_id);


--
-- Name: predictions predictions_pkey; Type: CONSTRAINT; Schema: model; Owner: -
--

ALTER TABLE ONLY model.predictions
    ADD CONSTRAINT predictions_pkey PRIMARY KEY (id);


--
-- Name: api_payloads api_payloads_pkey; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.api_payloads
    ADD CONSTRAINT api_payloads_pkey PRIMARY KEY (id);


--
-- Name: idx_agent_decisions_fixture; Type: INDEX; Schema: audit; Owner: -
--

CREATE INDEX idx_agent_decisions_fixture ON audit.agent_decisions USING btree (fixture_id, created_at DESC);


--
-- Name: idx_fixtures_kickoff; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_fixtures_kickoff ON core.fixtures USING btree (kickoff_at);


--
-- Name: idx_fixtures_selected; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_fixtures_selected ON core.fixtures USING btree (kickoff_at, selected_for_analysis);


--
-- Name: idx_fixtures_teams; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_fixtures_teams ON core.fixtures USING btree (home_team_id, away_team_id);


--
-- Name: idx_match_predictions_competition_season; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_match_predictions_competition_season ON core.match_predictions USING btree (competition_id, season_id, predicted_at DESC);


--
-- Name: idx_match_predictions_fixture; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_match_predictions_fixture ON core.match_predictions USING btree (fixture_id);


--
-- Name: idx_match_predictions_model_versions; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_match_predictions_model_versions ON core.match_predictions USING btree (expected_goals_model_version, probability_model_version, predicted_at DESC);


--
-- Name: idx_match_predictions_pending_evaluation; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_match_predictions_pending_evaluation ON core.match_predictions USING btree (result_confirmed, kickoff_at) WHERE (result_confirmed = false);


--
-- Name: idx_match_predictions_teams; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_match_predictions_teams ON core.match_predictions USING btree (home_team_id, away_team_id, predicted_at DESC);


--
-- Name: idx_standing_rows_snapshot; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_standing_rows_snapshot ON core.standing_rows USING btree (snapshot_id, "position");


--
-- Name: idx_standing_rows_team; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_standing_rows_team ON core.standing_rows USING btree (team_id, created_at DESC);


--
-- Name: idx_standing_snapshots_competition; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_standing_snapshots_competition ON core.standing_snapshots USING btree (competition_id, snapshot_at DESC);


--
-- Name: idx_standing_snapshots_raw_payload; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_standing_snapshots_raw_payload ON core.standing_snapshots USING btree (raw_payload_id);


--
-- Name: idx_standing_snapshots_season; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_standing_snapshots_season ON core.standing_snapshots USING btree (season_id, snapshot_at DESC);


--
-- Name: idx_team_snapshots_competition_time; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_team_snapshots_competition_time ON core.team_snapshots USING btree (competition_id, snapshot_at DESC);


--
-- Name: idx_team_snapshots_season; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_team_snapshots_season ON core.team_snapshots USING btree (season_id, team_id);


--
-- Name: idx_team_snapshots_team_time; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_team_snapshots_team_time ON core.team_snapshots USING btree (team_id, snapshot_at DESC);


--
-- Name: idx_team_snapshots_window; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_team_snapshots_window ON core.team_snapshots USING btree (window_size, snapshot_at DESC);


--
-- Name: uq_match_predictions_fixture_models; Type: INDEX; Schema: core; Owner: -
--

CREATE UNIQUE INDEX uq_match_predictions_fixture_models ON core.match_predictions USING btree (fixture_id, expected_goals_model_version, probability_model_version) WHERE (fixture_id IS NOT NULL);


--
-- Name: uq_team_snapshots_hash; Type: INDEX; Schema: core; Owner: -
--

CREATE UNIQUE INDEX uq_team_snapshots_hash ON core.team_snapshots USING btree (snapshot_hash) WHERE (snapshot_hash IS NOT NULL);


--
-- Name: uq_team_snapshots_identity; Type: INDEX; Schema: core; Owner: -
--

CREATE UNIQUE INDEX uq_team_snapshots_identity ON core.team_snapshots USING btree (team_id, competition_id, season_id, window_size, snapshot_at, calculation_version);


--
-- Name: idx_feature_fixture_time; Type: INDEX; Schema: model; Owner: -
--

CREATE INDEX idx_feature_fixture_time ON model.feature_snapshots USING btree (fixture_id, captured_at DESC);


--
-- Name: idx_predictions_fixture_stage; Type: INDEX; Schema: model; Owner: -
--

CREATE INDEX idx_predictions_fixture_stage ON model.predictions USING btree (fixture_id, prediction_stage, created_at DESC);


--
-- Name: idx_raw_payload_expiry; Type: INDEX; Schema: raw; Owner: -
--

CREATE INDEX idx_raw_payload_expiry ON raw.api_payloads USING btree (expires_at) WHERE (expires_at IS NOT NULL);


--
-- Name: idx_raw_payload_fixture; Type: INDEX; Schema: raw; Owner: -
--

CREATE INDEX idx_raw_payload_fixture ON raw.api_payloads USING btree (fixture_id, requested_at DESC);


--
-- Name: agent_decisions agent_decisions_fixture_id_fkey; Type: FK CONSTRAINT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.agent_decisions
    ADD CONSTRAINT agent_decisions_fixture_id_fkey FOREIGN KEY (fixture_id) REFERENCES core.fixtures(id) ON DELETE CASCADE;


--
-- Name: agent_decisions agent_decisions_prediction_id_fkey; Type: FK CONSTRAINT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.agent_decisions
    ADD CONSTRAINT agent_decisions_prediction_id_fkey FOREIGN KEY (prediction_id) REFERENCES model.predictions(id) ON DELETE CASCADE;


--
-- Name: supervisor_decisions supervisor_decisions_fixture_id_fkey; Type: FK CONSTRAINT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.supervisor_decisions
    ADD CONSTRAINT supervisor_decisions_fixture_id_fkey FOREIGN KEY (fixture_id) REFERENCES core.fixtures(id) ON DELETE CASCADE;


--
-- Name: supervisor_decisions supervisor_decisions_prediction_id_fkey; Type: FK CONSTRAINT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.supervisor_decisions
    ADD CONSTRAINT supervisor_decisions_prediction_id_fkey FOREIGN KEY (prediction_id) REFERENCES model.predictions(id) ON DELETE SET NULL;


--
-- Name: fixture_source_ids fixture_source_ids_fixture_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.fixture_source_ids
    ADD CONSTRAINT fixture_source_ids_fixture_id_fkey FOREIGN KEY (fixture_id) REFERENCES core.fixtures(id) ON DELETE CASCADE;


--
-- Name: fixture_source_ids fixture_source_ids_source_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.fixture_source_ids
    ADD CONSTRAINT fixture_source_ids_source_id_fkey FOREIGN KEY (source_id) REFERENCES core.data_sources(id) ON DELETE CASCADE;


--
-- Name: fixtures fixtures_away_team_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.fixtures
    ADD CONSTRAINT fixtures_away_team_id_fkey FOREIGN KEY (away_team_id) REFERENCES core.teams(id);


--
-- Name: fixtures fixtures_competition_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.fixtures
    ADD CONSTRAINT fixtures_competition_id_fkey FOREIGN KEY (competition_id) REFERENCES core.competitions(id) ON DELETE SET NULL;


--
-- Name: fixtures fixtures_home_team_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.fixtures
    ADD CONSTRAINT fixtures_home_team_id_fkey FOREIGN KEY (home_team_id) REFERENCES core.teams(id);


--
-- Name: fixtures fixtures_season_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.fixtures
    ADD CONSTRAINT fixtures_season_id_fkey FOREIGN KEY (season_id) REFERENCES core.seasons(id) ON DELETE SET NULL;


--
-- Name: fixtures fixtures_winner_team_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.fixtures
    ADD CONSTRAINT fixtures_winner_team_id_fkey FOREIGN KEY (winner_team_id) REFERENCES core.teams(id) ON DELETE SET NULL;


--
-- Name: match_predictions match_predictions_away_snapshot_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.match_predictions
    ADD CONSTRAINT match_predictions_away_snapshot_id_fkey FOREIGN KEY (away_snapshot_id) REFERENCES core.team_snapshots(id) ON DELETE SET NULL;


--
-- Name: match_predictions match_predictions_away_team_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.match_predictions
    ADD CONSTRAINT match_predictions_away_team_id_fkey FOREIGN KEY (away_team_id) REFERENCES core.teams(id) ON DELETE CASCADE;


--
-- Name: match_predictions match_predictions_competition_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.match_predictions
    ADD CONSTRAINT match_predictions_competition_id_fkey FOREIGN KEY (competition_id) REFERENCES core.competitions(id) ON DELETE CASCADE;


--
-- Name: match_predictions match_predictions_fixture_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.match_predictions
    ADD CONSTRAINT match_predictions_fixture_id_fkey FOREIGN KEY (fixture_id) REFERENCES core.fixtures(id) ON DELETE SET NULL;


--
-- Name: match_predictions match_predictions_home_snapshot_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.match_predictions
    ADD CONSTRAINT match_predictions_home_snapshot_id_fkey FOREIGN KEY (home_snapshot_id) REFERENCES core.team_snapshots(id) ON DELETE SET NULL;


--
-- Name: match_predictions match_predictions_home_team_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.match_predictions
    ADD CONSTRAINT match_predictions_home_team_id_fkey FOREIGN KEY (home_team_id) REFERENCES core.teams(id) ON DELETE CASCADE;


--
-- Name: match_predictions match_predictions_season_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.match_predictions
    ADD CONSTRAINT match_predictions_season_id_fkey FOREIGN KEY (season_id) REFERENCES core.seasons(id) ON DELETE CASCADE;


--
-- Name: seasons seasons_competition_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.seasons
    ADD CONSTRAINT seasons_competition_id_fkey FOREIGN KEY (competition_id) REFERENCES core.competitions(id) ON DELETE CASCADE;


--
-- Name: standing_rows standing_rows_snapshot_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.standing_rows
    ADD CONSTRAINT standing_rows_snapshot_id_fkey FOREIGN KEY (snapshot_id) REFERENCES core.standing_snapshots(id) ON DELETE CASCADE;


--
-- Name: standing_rows standing_rows_team_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.standing_rows
    ADD CONSTRAINT standing_rows_team_id_fkey FOREIGN KEY (team_id) REFERENCES core.teams(id) ON DELETE CASCADE;


--
-- Name: standing_snapshots standing_snapshots_competition_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.standing_snapshots
    ADD CONSTRAINT standing_snapshots_competition_id_fkey FOREIGN KEY (competition_id) REFERENCES core.competitions(id) ON DELETE CASCADE;


--
-- Name: standing_snapshots standing_snapshots_raw_payload_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.standing_snapshots
    ADD CONSTRAINT standing_snapshots_raw_payload_id_fkey FOREIGN KEY (raw_payload_id) REFERENCES raw.api_payloads(id) ON DELETE SET NULL;


--
-- Name: standing_snapshots standing_snapshots_season_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.standing_snapshots
    ADD CONSTRAINT standing_snapshots_season_id_fkey FOREIGN KEY (season_id) REFERENCES core.seasons(id) ON DELETE SET NULL;


--
-- Name: standing_snapshots standing_snapshots_source_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.standing_snapshots
    ADD CONSTRAINT standing_snapshots_source_id_fkey FOREIGN KEY (source_id) REFERENCES core.data_sources(id) ON DELETE CASCADE;


--
-- Name: team_aliases team_aliases_source_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.team_aliases
    ADD CONSTRAINT team_aliases_source_id_fkey FOREIGN KEY (source_id) REFERENCES core.data_sources(id) ON DELETE SET NULL;


--
-- Name: team_aliases team_aliases_team_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.team_aliases
    ADD CONSTRAINT team_aliases_team_id_fkey FOREIGN KEY (team_id) REFERENCES core.teams(id) ON DELETE CASCADE;


--
-- Name: team_snapshots team_snapshots_competition_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.team_snapshots
    ADD CONSTRAINT team_snapshots_competition_id_fkey FOREIGN KEY (competition_id) REFERENCES core.competitions(id) ON DELETE CASCADE;


--
-- Name: team_snapshots team_snapshots_season_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.team_snapshots
    ADD CONSTRAINT team_snapshots_season_id_fkey FOREIGN KEY (season_id) REFERENCES core.seasons(id) ON DELETE CASCADE;


--
-- Name: team_snapshots team_snapshots_team_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.team_snapshots
    ADD CONSTRAINT team_snapshots_team_id_fkey FOREIGN KEY (team_id) REFERENCES core.teams(id) ON DELETE CASCADE;


--
-- Name: team_source_ids team_source_ids_source_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.team_source_ids
    ADD CONSTRAINT team_source_ids_source_id_fkey FOREIGN KEY (source_id) REFERENCES core.data_sources(id) ON DELETE CASCADE;


--
-- Name: team_source_ids team_source_ids_team_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.team_source_ids
    ADD CONSTRAINT team_source_ids_team_id_fkey FOREIGN KEY (team_id) REFERENCES core.teams(id) ON DELETE CASCADE;


--
-- Name: feature_snapshots feature_snapshots_fixture_id_fkey; Type: FK CONSTRAINT; Schema: model; Owner: -
--

ALTER TABLE ONLY model.feature_snapshots
    ADD CONSTRAINT feature_snapshots_fixture_id_fkey FOREIGN KEY (fixture_id) REFERENCES core.fixtures(id) ON DELETE CASCADE;


--
-- Name: model_versions model_versions_parent_version_id_fkey; Type: FK CONSTRAINT; Schema: model; Owner: -
--

ALTER TABLE ONLY model.model_versions
    ADD CONSTRAINT model_versions_parent_version_id_fkey FOREIGN KEY (parent_version_id) REFERENCES model.model_versions(id) ON DELETE SET NULL;


--
-- Name: model_weights model_weights_model_version_id_fkey; Type: FK CONSTRAINT; Schema: model; Owner: -
--

ALTER TABLE ONLY model.model_weights
    ADD CONSTRAINT model_weights_model_version_id_fkey FOREIGN KEY (model_version_id) REFERENCES model.model_versions(id) ON DELETE CASCADE;


--
-- Name: prediction_evaluations prediction_evaluations_prediction_id_fkey; Type: FK CONSTRAINT; Schema: model; Owner: -
--

ALTER TABLE ONLY model.prediction_evaluations
    ADD CONSTRAINT prediction_evaluations_prediction_id_fkey FOREIGN KEY (prediction_id) REFERENCES model.predictions(id) ON DELETE CASCADE;


--
-- Name: predictions predictions_feature_snapshot_id_fkey; Type: FK CONSTRAINT; Schema: model; Owner: -
--

ALTER TABLE ONLY model.predictions
    ADD CONSTRAINT predictions_feature_snapshot_id_fkey FOREIGN KEY (feature_snapshot_id) REFERENCES model.feature_snapshots(id);


--
-- Name: predictions predictions_fixture_id_fkey; Type: FK CONSTRAINT; Schema: model; Owner: -
--

ALTER TABLE ONLY model.predictions
    ADD CONSTRAINT predictions_fixture_id_fkey FOREIGN KEY (fixture_id) REFERENCES core.fixtures(id) ON DELETE CASCADE;


--
-- Name: predictions predictions_model_version_id_fkey; Type: FK CONSTRAINT; Schema: model; Owner: -
--

ALTER TABLE ONLY model.predictions
    ADD CONSTRAINT predictions_model_version_id_fkey FOREIGN KEY (model_version_id) REFERENCES model.model_versions(id) ON DELETE SET NULL;


--
-- Name: api_payloads api_payloads_fixture_id_fkey; Type: FK CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.api_payloads
    ADD CONSTRAINT api_payloads_fixture_id_fkey FOREIGN KEY (fixture_id) REFERENCES core.fixtures(id) ON DELETE SET NULL;


--
-- Name: api_payloads api_payloads_source_id_fkey; Type: FK CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.api_payloads
    ADD CONSTRAINT api_payloads_source_id_fkey FOREIGN KEY (source_id) REFERENCES core.data_sources(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict vT9OyDk4OROIxTGFz2xlNyeTB9jhluwAk3ONoSJAxCsMEec0WM9fiMFIZUcZ1ld

-- v1 foundation: durable background job queue (migration 008_add_job_queue.sql)
CREATE TABLE core.schema_migrations (
    version text PRIMARY KEY,
    checksum text NOT NULL,
    applied_at timestamp with time zone NOT NULL DEFAULT now()
);

CREATE TABLE core.jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type text NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    status text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'retry', 'dead_letter')),
    idempotency_key text NOT NULL,
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    max_attempts integer NOT NULL DEFAULT 3 CHECK (max_attempts > 0),
    run_after timestamp with time zone NOT NULL DEFAULT now(),
    timeout_seconds integer NOT NULL DEFAULT 300 CHECK (timeout_seconds > 0),
    lease_expires_at timestamp with time zone,
    heartbeat_at timestamp with time zone,
    locked_by text,
    last_error text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    UNIQUE (job_type, idempotency_key)
);

CREATE INDEX idx_jobs_claimable ON core.jobs (status, run_after, created_at) WHERE status IN ('queued', 'retry');
CREATE INDEX idx_jobs_leases ON core.jobs (lease_expires_at) WHERE status = 'running';

-- v1 development: observable native scheduler (migration 009_add_worker_operations.sql)
CREATE TABLE core.worker_heartbeats (
    worker_id text PRIMARY KEY,
    status text NOT NULL CHECK (status IN ('idle', 'running', 'stopping')),
    heartbeat_at timestamp with time zone NOT NULL DEFAULT now(),
    current_job_id uuid REFERENCES core.jobs(id) ON DELETE SET NULL,
    scheduler_enabled boolean NOT NULL DEFAULT true,
    schedule_interval_seconds integer NOT NULL CHECK (schedule_interval_seconds > 0),
    next_sync_at timestamp with time zone,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    started_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

CREATE INDEX idx_worker_heartbeats_freshness ON core.worker_heartbeats (heartbeat_at DESC);
