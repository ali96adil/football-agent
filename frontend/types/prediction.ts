export interface Team {
  id: string;
  name: string;
  short_name?: string;
  logo_url?: string;
}

export interface Competition {
  id: string;
  name: string;
  country_code?: string;
}

export interface Prediction {
  id: string;
  fixture_id: string;

  kickoff_at: string;

  competition: Competition;

  home_team: Team;
  away_team: Team;

  predicted_outcome: string;

  confidence: number;

  home_expected_goals: number;
  away_expected_goals: number;
  total_expected_goals: number;

  home_win_probability: number;
  draw_probability: number;
  away_win_probability: number;

  most_likely_home_goals: number;
  most_likely_away_goals: number;

  actual_home_goals?: number | null;
  actual_away_goals?: number | null;
  actual_outcome?: string | null;

  outcome_correct?: boolean | null;
  score_correct?: boolean;
  result_confirmed?: boolean;
  evaluated_at?: string | null;
  exact_score_correct?: boolean | null;

  brier_score?: number | null;
  log_loss?: number | null;
    
}