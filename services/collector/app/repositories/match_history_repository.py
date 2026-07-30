from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.models.historical_match import HistoricalMatch


class MatchHistoryRepository:
    """Loads historical fixtures used for snapshot generation."""

    async def get_recent_completed_matches(
        self,
        connection: Any,
        *,
        team_id: UUID,
        before_kickoff: datetime,
        limit: int,
        competition_id: UUID | None = None,
        season_id: UUID | None = None,
    ) -> list[HistoricalMatch]:

        query = """
        SELECT
            id,
            kickoff_at,
            home_team_id,
            away_team_id,
            home_score,
            away_score
        FROM core.fixtures
        WHERE fixture_status = 'finished'
          AND kickoff_at < %s
          AND (
                home_team_id = %s
             OR away_team_id = %s
          )
        """

        params: list[Any] = [
            before_kickoff,
            team_id,
            team_id,
        ]

        if competition_id is not None:
            query += "\nAND competition_id = %s"
            params.append(competition_id)

        if season_id is not None:
            query += "\nAND season_id = %s"
            params.append(season_id)

        query += """
        ORDER BY kickoff_at DESC
        LIMIT %s
        """

        params.append(limit)

        result = await connection.execute(query, tuple(params))

        rows = await result.fetchall()

        matches: list[HistoricalMatch] = []

        for row in rows:

            is_home = row["home_team_id"] == team_id

            goals_for = row["home_score"] if is_home else row["away_score"]
            goals_against = row["away_score"] if is_home else row["home_score"]

            matches.append(
                HistoricalMatch(
                    fixture_id=row["id"],
                    kickoff_at=row["kickoff_at"],
                    home_team_id=row["home_team_id"],
                    away_team_id=row["away_team_id"],
                    home_score=row["home_score"],
                    away_score=row["away_score"],
                    is_home=is_home,
                    goals_for=goals_for,
                    goals_against=goals_against,
                    won=goals_for > goals_against,
                    drawn=goals_for == goals_against,
                    lost=goals_for < goals_against,
                    clean_sheet=goals_against == 0,
                    failed_to_score=goals_for == 0,
                    both_teams_scored=(
                        row["home_score"] > 0
                        and row["away_score"] > 0
                    ),
                    over_2_5=(
                        row["home_score"] + row["away_score"]
                    ) > 2,
                )
            )

        return matches