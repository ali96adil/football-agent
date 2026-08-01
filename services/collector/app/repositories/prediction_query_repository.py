from __future__ import annotations

from typing import Any

from app.api.schemas.prediction_response import (
    PredictionResponse,
    row_to_prediction_response,
)


PREDICTION_SELECT = """
    SELECT
        mp.*,

        ht.canonical_name AS home_team_name,
        ht.short_name AS home_team_short_name,
        ht.logo_url AS home_team_logo_url,

        at.canonical_name AS away_team_name,
        at.short_name AS away_team_short_name,
        at.logo_url AS away_team_logo_url,

        c.canonical_name AS competition_name,
        c.country_code AS competition_country_code

    FROM core.match_predictions AS mp

    INNER JOIN core.teams AS ht
        ON ht.id = mp.home_team_id

    INNER JOIN core.teams AS at
        ON at.id = mp.away_team_id

    INNER JOIN core.competitions AS c
        ON c.id = mp.competition_id
"""


class PredictionQueryRepository:
    async def get_predictions(
        self,
        connection: Any,
        *,
        limit: int = 50,
        offset: int = 0,
        view: str = "upcoming",
    ) -> list[PredictionResponse]:

        where_clause = ""

        if view == "upcoming":
            where_clause = """
                WHERE
                    mp.kickoff_at > NOW()
                    AND mp.result_confirmed = FALSE
            """

        elif view == "completed":
            where_clause = """
                WHERE
                    mp.result_confirmed = TRUE
             
            """

        order_clause = (
            "mp.kickoff_at ASC NULLS LAST, mp.fixture_id ASC"
            if view == "upcoming"
            else "mp.kickoff_at DESC NULLS LAST, mp.fixture_id ASC"
        )

        query = f"""
            {PREDICTION_SELECT}

            {where_clause}

            ORDER BY {order_clause}
            LIMIT %s
            OFFSET %s;
        """

        result = await connection.execute(
            query,
            (limit, offset),
        )

        rows = await result.fetchall()

        return [
            row_to_prediction_response(row)
            for row in rows
        ]

    async def get_prediction_by_fixture(
        self,
        connection: Any,
        fixture_id: str,
    ) -> PredictionResponse | None:
        query = f"""
            {PREDICTION_SELECT}

            WHERE mp.fixture_id = %s

            ORDER BY mp.predicted_at DESC
            LIMIT 1;
        """

        result = await connection.execute(
            query,
            (fixture_id,),
        )

        row = await result.fetchone()

        if row is None:
            return None

        return row_to_prediction_response(row)
