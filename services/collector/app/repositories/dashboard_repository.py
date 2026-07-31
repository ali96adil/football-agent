from typing import Any


class DashboardRepository:
    async def get_dashboard_stats(
        self,
        connection: Any,
    ) -> dict:
        query = """
        SELECT
            (SELECT COUNT(*) FROM core.fixtures) AS fixtures,

            (SELECT COUNT(*) FROM core.teams) AS teams,

            (SELECT COUNT(*) FROM core.competitions) AS competitions,

            (SELECT COUNT(*) FROM core.match_predictions) AS predictions,

            (
                SELECT COUNT(*)
                FROM core.fixtures
                WHERE fixture_status='scheduled'
            ) AS scheduled,

            (
                SELECT COUNT(*)
                FROM core.fixtures
                WHERE fixture_status='live'
            ) AS live,

            (
                SELECT COUNT(*)
                FROM core.fixtures
                WHERE result_confirmed = TRUE
            ) AS finished;
        """

        result = await connection.execute(query)

        row = await result.fetchone()

        return {
            "fixtures": int(row["fixtures"]),
            "teams": int(row["teams"]),
            "competitions": int(row["competitions"]),
            "predictions": int(row["predictions"]),
            "scheduled": int(row["scheduled"]),
            "live": int(row["live"]),
            "finished": int(row["finished"]),
        }
