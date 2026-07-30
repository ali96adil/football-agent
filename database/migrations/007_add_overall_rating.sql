BEGIN;

ALTER TABLE core.team_snapshots
ADD COLUMN IF NOT EXISTS overall_rating numeric(10,4);

COMMENT ON COLUMN core.team_snapshots.overall_rating IS
'Overall composite rating calculated from attack, defence, home, away and form ratings.';

COMMIT;