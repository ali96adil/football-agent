from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from app.db.connection import pool
from app.services.snapshot_service import SnapshotService


WINDOW_SIZE = 10


async def select_test_team(connection: Any) -> dict[str, Any]:
    """
    Select a team/competition/season combination that has the largest
    number of confirmed completed fixtures.
    """

    query = """
        WITH team_fixtures AS (
            SELECT
                home_team_id AS team_id,
                competition_id,
                season_id,
                kickoff_at
            FROM core.fixtures
            WHERE result_confirmed = TRUE
              AND home_score IS NOT NULL
              AND away_score IS NOT NULL
              AND home_team_id IS NOT NULL
              AND competition_id IS NOT NULL
              AND season_id IS NOT NULL

            UNION ALL

            SELECT
                away_team_id AS team_id,
                competition_id,
                season_id,
                kickoff_at
            FROM core.fixtures
            WHERE result_confirmed = TRUE
              AND home_score IS NOT NULL
              AND away_score IS NOT NULL
              AND away_team_id IS NOT NULL
              AND competition_id IS NOT NULL
              AND season_id IS NOT NULL
        )
        SELECT
            team_id,
            competition_id,
            season_id,
            COUNT(*) AS fixture_count,
            MAX(kickoff_at) AS data_cutoff_at
        FROM team_fixtures
        GROUP BY
            team_id,
            competition_id,
            season_id
        ORDER BY
            fixture_count DESC,
            data_cutoff_at DESC
        LIMIT 1
    """

    result = await connection.execute(query)
    row = await result.fetchone()

    if row is None:
        raise RuntimeError(
            "No completed confirmed fixtures were found in core.fixtures."
        )

    return row


async def count_snapshots_by_hash(
    connection: Any,
    *,
    snapshot_hash: str,
) -> int:
    result = await connection.execute(
        """
        SELECT COUNT(*) AS snapshot_count
        FROM core.team_snapshots
        WHERE snapshot_hash = %s
        """,
        (snapshot_hash,),
    )

    row = await result.fetchone()

    return int(row["snapshot_count"])


async def main() -> None:
    await pool.open()
    await pool.wait()

    try:
        async with pool.connection() as connection:
            selected = await select_test_team(connection)

            team_id = UUID(str(selected["team_id"]))
            competition_id = UUID(str(selected["competition_id"]))
            season_id = UUID(str(selected["season_id"]))
            data_cutoff_at = selected["data_cutoff_at"]
            available_fixtures = int(selected["fixture_count"])

            print("=" * 72)
            print("TEAM SNAPSHOT INTEGRATION TEST")
            print("=" * 72)
            print(f"Team ID            : {team_id}")
            print(f"Competition ID     : {competition_id}")
            print(f"Season ID          : {season_id}")
            print(f"Available fixtures : {available_fixtures}")
            print(f"Window size        : {WINDOW_SIZE}")
            print(f"Data cutoff        : {data_cutoff_at}")
            print("-" * 72)

            first_snapshot = await SnapshotService.build_and_save(
                connection=connection,
                team_id=team_id,
                competition_id=competition_id,
                season_id=season_id,
                window_size=WINDOW_SIZE,
                cutoff_at=data_cutoff_at,
            )

            if first_snapshot.snapshot_hash is None:
                raise RuntimeError(
                    "The first snapshot was saved without snapshot_hash."
                )

            count_after_first = await count_snapshots_by_hash(
                connection,
                snapshot_hash=first_snapshot.snapshot_hash,
            )

            second_snapshot = await SnapshotService.build_and_save(
                connection=connection,
                team_id=team_id,
                competition_id=competition_id,
                season_id=season_id,
                window_size=WINDOW_SIZE,
                cutoff_at=data_cutoff_at,
            )

            if second_snapshot.snapshot_hash is None:
                raise RuntimeError(
                    "The second snapshot was saved without snapshot_hash."
                )

            count_after_second = await count_snapshots_by_hash(
                connection,
                snapshot_hash=second_snapshot.snapshot_hash,
            )

            same_hash = (
                first_snapshot.snapshot_hash
                == second_snapshot.snapshot_hash
            )

            same_database_id = (
                first_snapshot.id
                == second_snapshot.id
            )

            duplicate_prevention_ok = (
                same_hash
                and same_database_id
                and count_after_first == 1
                and count_after_second == 1
            )

            print("FIRST BUILD")
            print(f"Snapshot ID        : {first_snapshot.id}")
            print(f"Matches played     : {first_snapshot.matches_played}")
            print(f"Form sequence      : {first_snapshot.form_sequence}")
            print(f"Points per game    : {first_snapshot.points_per_game}")
            print(f"Attack rating      : {first_snapshot.attack_rating}")
            print(f"Defence rating     : {first_snapshot.defence_rating}")
            print(f"Form rating        : {first_snapshot.form_rating}")
            print(f"Home rating        : {first_snapshot.home_rating}")
            print(f"Away rating        : {first_snapshot.away_rating}")
            print(f"Overall rating     : {first_snapshot.overall_rating}")
            print(f"Data completeness  : {first_snapshot.data_completeness}")
            print(f"Snapshot hash      : {first_snapshot.snapshot_hash}")
            print("-" * 72)

            print("DUPLICATE-PREVENTION CHECK")
            print(f"Second snapshot ID : {second_snapshot.id}")
            print(f"Same hash          : {same_hash}")
            print(f"Same database ID   : {same_database_id}")
            print(f"Count after first  : {count_after_first}")
            print(f"Count after second : {count_after_second}")
            print("-" * 72)

            if not duplicate_prevention_ok:
                raise RuntimeError(
                    "Duplicate-prevention test failed. "
                    "Expected the same hash, same ID and one database row."
                )

            print("RESULT              : PASSED")
            print("=" * 72)

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
