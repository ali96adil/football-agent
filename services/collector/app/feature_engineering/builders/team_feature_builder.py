from __future__ import annotations

from app.domain.team_snapshot import TeamSnapshot
from app.feature_engineering.domain.feature import Feature


class TeamFeatureBuilder:
    """
    Convert one TeamSnapshot into prediction-ready team features.
    """

    @classmethod
    def build(
        cls,
        snapshot: TeamSnapshot,
        *,
        prefix: str,
    ) -> list[Feature]:
        prefix = prefix.strip().lower()

        if prefix not in {"home", "away"}:
            raise ValueError(
                "prefix must be either 'home' or 'away'."
            )

        return [
            Feature(
                name=f"{prefix}_overall_rating",
                value=snapshot.overall_rating,
                category="rating",
                source="team_snapshot",
                importance="critical",
            ),
            Feature(
                name=f"{prefix}_attack_rating",
                value=snapshot.attack_rating,
                category="rating",
                source="team_snapshot",
                importance="high",
            ),
            Feature(
                name=f"{prefix}_defence_rating",
                value=snapshot.defence_rating,
                category="rating",
                source="team_snapshot",
                importance="high",
            ),
            Feature(
                name=f"{prefix}_form_rating",
                value=snapshot.form_rating,
                category="rating",
                source="team_snapshot",
                importance="high",
            ),
            Feature(
                name=f"{prefix}_venue_rating",
                value=(
                    snapshot.home_rating
                    if prefix == "home"
                    else snapshot.away_rating
                ),
                category="rating",
                source="team_snapshot",
                importance="high",
            ),
            Feature(
                name=f"{prefix}_elo_rating",
                value=snapshot.elo_rating,
                category="rating",
                source="team_snapshot",
                importance="critical",
            ),
            Feature(
                name=f"{prefix}_points_per_game",
                value=snapshot.points_per_game,
                category="performance",
                source="team_snapshot",
                importance="high",
            ),
            Feature(
                name=f"{prefix}_goals_for_per_game",
                value=snapshot.goals_for_per_game,
                category="attack",
                source="team_snapshot",
                importance="high",
            ),
            Feature(
                name=f"{prefix}_goals_against_per_game",
                value=snapshot.goals_against_per_game,
                category="defence",
                source="team_snapshot",
                importance="high",
            ),
            Feature(
                name=f"{prefix}_venue_points_per_game",
                value=(
                    snapshot.home_points_per_game
                    if prefix == "home"
                    else snapshot.away_points_per_game
                ),
                category="venue",
                source="team_snapshot",
                importance="high",
            ),
            Feature(
                name=f"{prefix}_venue_goals_for_per_game",
                value=(
                    snapshot.home_goals_for_per_game
                    if prefix == "home"
                    else snapshot.away_goals_for_per_game
                ),
                category="venue",
                source="team_snapshot",
                importance="high",
            ),
            Feature(
                name=f"{prefix}_venue_goals_against_per_game",
                value=(
                    snapshot.home_goals_against_per_game
                    if prefix == "home"
                    else snapshot.away_goals_against_per_game
                ),
                category="venue",
                source="team_snapshot",
                importance="high",
            ),
            Feature(
                name=f"{prefix}_goal_difference",
                value=snapshot.goal_difference,
                category="performance",
                source="team_snapshot",
                importance="normal",
            ),
            Feature(
                name=f"{prefix}_clean_sheet_rate",
                value=snapshot.clean_sheet_rate,
                category="defence",
                source="team_snapshot",
                importance="normal",
            ),
            Feature(
                name=f"{prefix}_failed_to_score_rate",
                value=snapshot.failed_to_score_rate,
                category="attack",
                source="team_snapshot",
                importance="normal",
            ),
            Feature(
                name=f"{prefix}_btts_rate",
                value=snapshot.btts_rate,
                category="goals_market",
                source="team_snapshot",
                importance="normal",
            ),
            Feature(
                name=f"{prefix}_over_2_5_rate",
                value=snapshot.over_2_5_rate,
                category="goals_market",
                source="team_snapshot",
                importance="normal",
            ),
            Feature(
                name=f"{prefix}_days_since_last_match",
                value=snapshot.days_since_last_match,
                category="schedule",
                source="team_snapshot",
                importance="normal",
            ),
            Feature(
                name=f"{prefix}_league_position",
                value=snapshot.current_position,
                category="standing",
                source="team_snapshot",
                importance="normal",
            ),
            Feature(
                name=f"{prefix}_league_points",
                value=snapshot.current_league_points,
                category="standing",
                source="team_snapshot",
                importance="normal",
            ),
            Feature(
                name=f"{prefix}_matches_played",
                value=snapshot.matches_played,
                category="data_quality",
                source="team_snapshot",
                importance="low",
            ),
            Feature(
                name=f"{prefix}_data_completeness",
                value=snapshot.data_completeness,
                category="data_quality",
                source="team_snapshot",
                importance="high",
            ),
        ]
