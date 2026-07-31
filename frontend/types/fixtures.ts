export interface FixtureTeam {
  id?: number | string | null
  name: string
  short_name?: string | null
  logo?: string | null
  crest?: string | null
  crest_url?: string | null
}

export interface FixtureCompetition {
  id?: number | string | null
  name: string
  logo?: string | null
  emblem?: string | null
}

export interface Fixture {
  id: number | string
  status: string

  kickoff_at?: string | null
  utc_date?: string | null
  date?: string | null
  scheduled_at?: string | null

  competition?: FixtureCompetition | null
  competition_id?: number | string | null
  competition_name?: string | null
  competition_logo?: string | null

  home_team?: FixtureTeam | null
  away_team?: FixtureTeam | null

  home_team_id?: number | string | null
  away_team_id?: number | string | null

  home_team_name?: string | null
  away_team_name?: string | null

  home_team_logo?: string | null
  away_team_logo?: string | null

  home_score?: number | null
  away_score?: number | null
  score_home?: number | null
  score_away?: number | null
}

export interface FixturesResponse {
  items: Fixture[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface FixturesQuery {
  page?: number
  page_size?: number
  search?: string
  status?: string
  competition_id?: number | string
  team_id?: number | string
  date?: string
  sort?: string
}
