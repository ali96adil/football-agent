BEGIN;

ALTER TABLE core.fixtures
ADD CONSTRAINT fixtures_unique_match
UNIQUE (
    competition_id,
    kickoff_at,
    home_team_id,
    away_team_id
);

COMMIT;
