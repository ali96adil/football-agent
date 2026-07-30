import json
from typing import Any


async def insert_standing_snapshot(
    connection: Any,
    competition_id: str,
    season_id: str | None,
    source_id: int,
    raw_payload_id: int,
    competition_code: str,
    standing_type: str,
    metadata: dict[str, Any],
) -> str:
    result = await connection.execute(
        """
        INSERT INTO core.standing_snapshots (
            competition_id,
            season_id,
            source_id,
            raw_payload_id,
            competition_code,
            standing_type,
            metadata
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s::jsonb
        )
        RETURNING id
        """,
        (
            competition_id,
            season_id,
            source_id,
            raw_payload_id,
            competition_code,
            standing_type,
            json.dumps(metadata, ensure_ascii=False),
        ),
    )

    row = await result.fetchone()
    return str(row["id"])


async def insert_standing_row(
    connection: Any,
    snapshot_id: str,
    team_id: str,
    row: dict[str, Any],
) -> None:

    await connection.execute(
        """
        INSERT INTO core.standing_rows (
            snapshot_id,
            team_id,
            position,
            played_games,
            won,
            draw,
            lost,
            points,
            goals_for,
            goals_against,
            goal_difference,
            form,
            metadata
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s::jsonb
        )
        """,
        (
            snapshot_id,
            team_id,
            row["position"],
            row["played_games"],
            row["won"],
            row["draw"],
            row["lost"],
            row["points"],
            row["goals_for"],
            row["goals_against"],
            row["goal_difference"],
            row.get("form"),
            json.dumps({}, ensure_ascii=False),
        ),
    )