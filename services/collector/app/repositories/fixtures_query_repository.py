from datetime import date
from typing import Any
from uuid import UUID


class FixturesQueryRepository:
    async def get_fixtures(
        self,
        connection: Any,
        *,
        offset: int,
        limit: int,
        status: str | None = None,
        competition_id: UUID | None = None,
        team_id: UUID | None = None,
        fixture_date: date | None = None,
        search: str | None = None,
        sort: str = "newest",
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[str] = []
        parameters: list[Any] = []

        if status:
            conditions.append(
                "LOWER(f.fixture_status) = LOWER(%s)"
            )
            parameters.append(status)

        if competition_id:
            conditions.append("f.competition_id = %s")
            parameters.append(competition_id)

        if team_id:
            conditions.append(
                """
                (
                    f.home_team_id = %s
                    OR f.away_team_id = %s
                )
                """
            )
            parameters.extend([team_id, team_id])

        if fixture_date:
            conditions.append("f.kickoff_at::date = %s")
            parameters.append(fixture_date)

        normalized_search = (
            search.strip()
            if search and search.strip()
            else None
        )

        if normalized_search:
            search_value = f"%{normalized_search}%"

            conditions.append(
                """
                (
                    ht.canonical_name ILIKE %s
                    OR ht.short_name ILIKE %s
                    OR at.canonical_name ILIKE %s
                    OR at.short_name ILIKE %s
                    OR c.canonical_name ILIKE %s
                    OR f.venue_name ILIKE %s
                    OR f.venue_city ILIKE %s
                )
                """
            )

            parameters.extend([search_value] * 7)

        where_clause = (
            f"WHERE {' AND '.join(conditions)}"
            if conditions
            else ""
        )

        order_by_map = {
            "newest": "f.kickoff_at DESC, f.id DESC",
            "oldest": "f.kickoff_at ASC, f.id ASC",
            "upcoming": """
                CASE
                    WHEN f.kickoff_at >= NOW() THEN 0
                    ELSE 1
                END,
                f.kickoff_at ASC,
                f.id ASC
            """,
        }

        order_by = order_by_map.get(
            sort,
            order_by_map["newest"],
        )

        count_query = f"""
            SELECT COUNT(*) AS total
            FROM core.fixtures f
            JOIN core.teams ht
              ON ht.id = f.home_team_id
            JOIN core.teams at
              ON at.id = f.away_team_id
            LEFT JOIN core.competitions c
              ON c.id = f.competition_id
            {where_clause}
        """

        count_result = await connection.execute(
            count_query,
            tuple(parameters),
        )

        count_row = await count_result.fetchone()
        total = int(count_row["total"])

        data_parameters = [
            *parameters,
            limit,
            offset,
        ]

        fixtures_query = f"""
            SELECT
                f.id,
                f.kickoff_at,
                f.fixture_status,
                f.venue_name,
                f.venue_city,
                f.neutral_venue,
                f.home_score,
                f.away_score,
                f.extra_time_home,
                f.extra_time_away,
                f.penalties_home,
                f.penalties_away,
                f.result_confirmed,
                f.selected_for_analysis,

                ht.id AS home_team_id,
                ht.canonical_name AS home_team_name,
                ht.short_name AS home_team_short_name,
                ht.country_code AS home_team_country_code,
                ht.logo_url AS home_team_logo_url,

                at.id AS away_team_id,
                at.canonical_name AS away_team_name,
                at.short_name AS away_team_short_name,
                at.country_code AS away_team_country_code,
                at.logo_url AS away_team_logo_url,

                c.id AS competition_id,
                c.canonical_name AS competition_name,
                c.country_code AS competition_country_code,
                c.competition_type

            FROM core.fixtures f

            JOIN core.teams ht
              ON ht.id = f.home_team_id

            JOIN core.teams at
              ON at.id = f.away_team_id

            LEFT JOIN core.competitions c
              ON c.id = f.competition_id

            {where_clause}

            ORDER BY {order_by}

            LIMIT %s
            OFFSET %s
        """

        fixtures_result = await connection.execute(
            fixtures_query,
            tuple(data_parameters),
        )

        rows = await fixtures_result.fetchall()

        return list(rows), total
