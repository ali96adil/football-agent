from __future__ import annotations
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


import asyncio

from app.db.connection import open_connection_pool, close_connection_pool
from app.repositories.match_history_repository import MatchHistoryRepository
from app.services.snapshot_calculator import SnapshotCalculator


async def main() -> None:

    await open_connection_pool()

    try:

        from app.db.connection import pool

        async with pool.connection() as connection:

            result = await connection.execute(
                """
                SELECT
                    home_team_id,
                    competition_id,
                    season_id,
                    kickoff_at
                FROM core.fixtures
                WHERE fixture_status = 'finished'
                ORDER BY kickoff_at DESC
                LIMIT 1
                """
            )

            fixture = await result.fetchone()

            if fixture is None:
                print("No finished fixtures found.")
                return

            repo = MatchHistoryRepository()

            matches = await repo.get_recent_completed_matches(
                connection,
                team_id=fixture["home_team_id"],
                competition_id=fixture["competition_id"],
                season_id=fixture["season_id"],
                before_kickoff=fixture["kickoff_at"],
                limit=10,
            )

            calculator = SnapshotCalculator()

            metrics = calculator.calculate(
                matches=matches,
                expected_window_size=10,
            )

            print()
            print("========== SNAPSHOT ==========")
            print(metrics)
            print("==============================")
            print()

    finally:
        await close_connection_pool()


if __name__ == "__main__":
    asyncio.run(main())