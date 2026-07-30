from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb

from app.models.team_snapshot import TeamSnapshot


class SnapshotRepository:
    """Persistence layer for team snapshots."""

    async def insert_snapshot(
        self,
        connection: Any,
        *,
        snapshot: TeamSnapshot,
    ) -> UUID:
        query = """
        INSERT INTO core.team_snapshots (
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
            goals_for,
            goals_against,
            goal_difference,
            points_per_game,
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
            away_matches,
            away_wins,
            away_draws,
            away_losses,
            away_points,
            form_sequence,
            data_completeness,
            calculation_version,
            snapshot_hash,
            metadata
        )
        VALUES (
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s
        )
        RETURNING id
        """

        params = (
            snapshot.team_id,
            snapshot.competition_id,
            snapshot.season_id,
            snapshot.snapshot_at,
            snapshot.data_cutoff_at,
            snapshot.window_size,
            snapshot.matches_played,
            snapshot.wins,
            snapshot.draws,
            snapshot.losses,
            snapshot.points,
            snapshot.goals_for,
            snapshot.goals_against,
            snapshot.goal_difference,
            snapshot.points_per_game,
            snapshot.goals_for_per_game,
            snapshot.goals_against_per_game,
            snapshot.clean_sheets,
            snapshot.failed_to_score,
            snapshot.btts_count,
            snapshot.over_2_5_count,
            snapshot.btts_rate,
            snapshot.over_2_5_rate,
            snapshot.clean_sheet_rate,
            snapshot.failed_to_score_rate,
            snapshot.home_matches,
            snapshot.home_wins,
            snapshot.home_draws,
            snapshot.home_losses,
            snapshot.home_points,
            snapshot.away_matches,
            snapshot.away_wins,
            snapshot.away_draws,
            snapshot.away_losses,
            snapshot.away_points,
            snapshot.form_sequence,
            snapshot.data_completeness,
            snapshot.calculation_version,
            snapshot.snapshot_hash,
            Jsonb(snapshot.metadata),
        )

        result = await connection.execute(query, params)

        row = await result.fetchone()

        return UUID(str(row["id"]))

    async def get_latest_snapshot(
        self,
        connection: Any,
        *,
        team_id: UUID,
        competition_id: UUID,
        season_id: UUID,
        window_size: int,
    ) -> TeamSnapshot | None:
        raise NotImplementedError