from __future__ import annotations

from typing import Any


def normalize_standings(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize football-data.org standings payload into
    snapshot + standing rows.
    """

    competition = payload["competition"]
    season = payload["season"]

    standings = payload.get("standings", [])

    if not standings:
        raise ValueError("No standings found in payload.")

    table = standings[0]

    snapshot = {
        "competition": competition,
        "season": season,
        "standing_type": table.get("type", "TOTAL"),
        "stage": table.get("stage"),
        "group": table.get("group"),
    }

    rows = []

    for row in table.get("table", []):
        rows.append(
            {
                "team": row["team"],
                "position": row["position"],
                "played_games": row["playedGames"],
                "won": row["won"],
                "draw": row["draw"],
                "lost": row["lost"],
                "points": row["points"],
                "goals_for": row["goalsFor"],
                "goals_against": row["goalsAgainst"],
                "goal_difference": row["goalDifference"],
                "form": row.get("form"),
            }
        )

    return {
        "snapshot": snapshot,
        "rows": rows,
    }