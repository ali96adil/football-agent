from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.db.connection import pool
from app.services.snapshot_service import SnapshotService


@dataclass(frozen=True)
class TeamTarget:
    team_id: UUID
    competition_id: UUID
    season_id: UUID
    fixture_count: int
    data_cutoff_at: datetime


def parse_uuid(value: str | None) -> UUID | None:
    if value is None:
        return None

    try:
        return UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid UUID: {value}"
        ) from exc


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build and save team snapshots for all teams that have "
            "completed confirmed fixtures."
        )
    )

    parser.add_argument(
        "--window-size",
        type=int,
        default=10,
        help="Number of recent completed fixtures used per team. Default: 10",
    )

    parser.add_argument(
        "--competition-id",
        type=parse_uuid,
        default=None,
        help="Optional competition UUID filter.",
    )

    parser.add_argument(
        "--season-id",
        type=parse_uuid,
        default=None,
        help="Optional season UUID filter.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of teams to process.",
    )

    args = parser.parse_args()

    if args.window_size < 1:
        parser.error("--window-size must be greater than zero")

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be greater than zero")

    return args


async def get_snapshot_count(
    connection: Any,
) -> int:
    result = await connection.execute(
        """
        SELECT COUNT(*) AS snapshot_count
        FROM core.team_snapshots
        """
    )

    row = await result.fetchone()

    return int(row["snapshot_count"])


async def get_team_targets(
    connection: Any,
    *,
    competition_id: UUID | None,
    season_id: UUID | None,
    limit: int | None,
) -> list[TeamTarget]:
    conditions = [
        "result_confirmed = TRUE",
        "home_score IS NOT NULL",
        "away_score IS NOT NULL",
        "competition_id IS NOT NULL",
        "season_id IS NOT NULL",
    ]

    parameters: list[Any] = []

    if competition_id is not None:
        conditions.append("competition_id = %s")
        parameters.append(competition_id)

    if season_id is not None:
        conditions.append("season_id = %s")
        parameters.append(season_id)

    where_clause = " AND ".join(conditions)

    limit_clause = ""

    if limit is not None:
        limit_clause = "LIMIT %s"
        parameters.append(limit)

    query = f"""
        WITH team_fixtures AS (
            SELECT
                home_team_id AS team_id,
                competition_id,
                season_id,
                kickoff_at
            FROM core.fixtures
            WHERE {where_clause}
              AND home_team_id IS NOT NULL

            UNION ALL

            SELECT
                away_team_id AS team_id,
                competition_id,
                season_id,
                kickoff_at
            FROM core.fixtures
            WHERE {where_clause}
              AND away_team_id IS NOT NULL
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
            competition_id,
            season_id,
            fixture_count DESC,
            team_id
        {limit_clause}
    """

    # The competition and season parameters appear twice because the
    # conditions are used in both sides of UNION ALL.
    duplicated_filter_parameters: list[Any] = []

    if competition_id is not None:
        duplicated_filter_parameters.append(competition_id)

    if season_id is not None:
        duplicated_filter_parameters.append(season_id)

    query_parameters = (
        duplicated_filter_parameters
        + duplicated_filter_parameters
    )

    if limit is not None:
        query_parameters.append(limit)

    result = await connection.execute(
        query,
        tuple(query_parameters),
    )

    rows = await result.fetchall()

    return [
        TeamTarget(
            team_id=UUID(str(row["team_id"])),
            competition_id=UUID(str(row["competition_id"])),
            season_id=UUID(str(row["season_id"])),
            fixture_count=int(row["fixture_count"]),
            data_cutoff_at=row["data_cutoff_at"],
        )
        for row in rows
    ]


async def main() -> None:
    args = parse_arguments()

    await pool.open()
    await pool.wait()

    try:
        async with pool.connection() as connection:
            targets = await get_team_targets(
                connection,
                competition_id=args.competition_id,
                season_id=args.season_id,
                limit=args.limit,
            )

            if not targets:
                print("=" * 80)
                print("No eligible team targets were found.")
                print("=" * 80)
                return

            snapshots_before = await get_snapshot_count(connection)

            successful = 0
            failed = 0
            complete = 0
            partial = 0

            failures: list[tuple[TeamTarget, str]] = []

            print("=" * 80)
            print("BATCH TEAM SNAPSHOT BUILDER")
            print("=" * 80)
            print(f"Targets found       : {len(targets)}")
            print(f"Window size         : {args.window_size}")
            print(f"Competition filter  : {args.competition_id or 'ALL'}")
            print(f"Season filter       : {args.season_id or 'ALL'}")
            print(f"Snapshots before    : {snapshots_before}")
            print("=" * 80)

            for index, target in enumerate(targets, start=1):
                print(
                    f"[{index:>3}/{len(targets)}] "
                    f"Team {target.team_id} | "
                    f"fixtures={target.fixture_count}",
                    end=" ... ",
                    flush=True,
                )

                try:
                    snapshot = await SnapshotService.build_and_save(
                        connection=connection,
                        team_id=target.team_id,
                        competition_id=target.competition_id,
                        season_id=target.season_id,
                        window_size=args.window_size,
                        cutoff_at=target.data_cutoff_at,
                    )

                    successful += 1

                    if snapshot.data_completeness >= 1:
                        complete += 1
                    else:
                        partial += 1

                    print(
                        "OK | "
                        f"matches={snapshot.matches_played} | "
                        f"overall={snapshot.overall_rating} | "
                        f"completeness={snapshot.data_completeness}"
                    )

                except Exception as exc:
                    failed += 1
                    failures.append((target, str(exc)))

                    print(
                        f"FAILED | {type(exc).__name__}: {exc}"
                    )

            snapshots_after = await get_snapshot_count(connection)

            print("=" * 80)
            print("BATCH RESULT")
            print("=" * 80)
            print(f"Targets processed   : {len(targets)}")
            print(f"Successful          : {successful}")
            print(f"Failed              : {failed}")
            print(f"Complete snapshots  : {complete}")
            print(f"Partial snapshots   : {partial}")
            print(f"Snapshots before    : {snapshots_before}")
            print(f"Snapshots after     : {snapshots_after}")
            print(f"New database rows   : {snapshots_after - snapshots_before}")

            if failures:
                print("-" * 80)
                print("FAILURES")

                for target, error in failures:
                    print(
                        f"Team={target.team_id} | "
                        f"Competition={target.competition_id} | "
                        f"Season={target.season_id} | "
                        f"Error={error}"
                    )

            print("=" * 80)

            if failed == 0:
                print("RESULT              : PASSED")
            elif successful > 0:
                print("RESULT              : PARTIAL SUCCESS")
            else:
                raise RuntimeError(
                    "Batch snapshot generation failed for every target."
                )

            print("=" * 80)

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
