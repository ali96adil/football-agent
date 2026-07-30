from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.domain.team_snapshot import TeamSnapshot
from app.feature_engineering.builders.team_feature_builder import (
    TeamFeatureBuilder,
)
from app.feature_engineering.domain.feature import Feature
from app.feature_engineering.domain.feature_vector import FeatureVector


class MatchFeatureBuilder:
    """
    Build a prediction-ready feature vector from home and away snapshots.
    """

    @classmethod
    def build(
        cls,
        *,
        home_snapshot: TeamSnapshot,
        away_snapshot: TeamSnapshot,
        metadata: dict[str, Any] | None = None,
    ) -> FeatureVector:
        cls._validate_snapshots(
            home_snapshot=home_snapshot,
            away_snapshot=away_snapshot,
        )

        vector = FeatureVector(
            home_team_id=home_snapshot.team_id,
            away_team_id=away_snapshot.team_id,
            competition_id=home_snapshot.competition_id,
            season_id=home_snapshot.season_id,
            home_snapshot_id=home_snapshot.id,
            away_snapshot_id=away_snapshot.id,
            generated_at=datetime.now(timezone.utc),
            metadata=dict(metadata or {}),
        )

        vector.extend(
            TeamFeatureBuilder.build(
                home_snapshot,
                prefix="home",
            )
        )

        vector.extend(
            TeamFeatureBuilder.build(
                away_snapshot,
                prefix="away",
            )
        )

        vector.extend(
            cls._build_comparison_features(
                home_snapshot=home_snapshot,
                away_snapshot=away_snapshot,
            )
        )

        return vector

    @classmethod
    def _build_comparison_features(
        cls,
        *,
        home_snapshot: TeamSnapshot,
        away_snapshot: TeamSnapshot,
    ) -> list[Feature]:
        return [
            cls._difference_feature(
                name="overall_rating_difference",
                home_value=home_snapshot.overall_rating,
                away_value=away_snapshot.overall_rating,
                category="rating_comparison",
                importance="critical",
                description=(
                    "Home overall rating minus away overall rating."
                ),
            ),
            cls._difference_feature(
                name="elo_rating_difference",
                home_value=home_snapshot.elo_rating,
                away_value=away_snapshot.elo_rating,
                category="rating_comparison",
                importance="critical",
                description="Home Elo rating minus away Elo rating.",
            ),
            cls._difference_feature(
                name="form_rating_difference",
                home_value=home_snapshot.form_rating,
                away_value=away_snapshot.form_rating,
                category="form_comparison",
                importance="high",
                description="Home form rating minus away form rating.",
            ),
            cls._difference_feature(
                name="venue_rating_difference",
                home_value=home_snapshot.home_rating,
                away_value=away_snapshot.away_rating,
                category="venue_comparison",
                importance="high",
                description=(
                    "Home team's home rating minus away team's away rating."
                ),
            ),
            cls._difference_feature(
                name="points_per_game_difference",
                home_value=home_snapshot.points_per_game,
                away_value=away_snapshot.points_per_game,
                category="performance_comparison",
                importance="high",
                description=(
                    "Home points per game minus away points per game."
                ),
            ),
            cls._difference_feature(
                name="venue_points_per_game_difference",
                home_value=home_snapshot.home_points_per_game,
                away_value=away_snapshot.away_points_per_game,
                category="venue_comparison",
                importance="high",
                description=(
                    "Home venue PPG minus away venue PPG."
                ),
            ),
            cls._difference_feature(
                name="attack_rating_difference",
                home_value=home_snapshot.attack_rating,
                away_value=away_snapshot.attack_rating,
                category="rating_comparison",
                importance="high",
                description=(
                    "Home attack rating minus away attack rating."
                ),
            ),
            cls._difference_feature(
                name="defence_rating_difference",
                home_value=home_snapshot.defence_rating,
                away_value=away_snapshot.defence_rating,
                category="rating_comparison",
                importance="high",
                description=(
                    "Home defence rating minus away defence rating."
                ),
            ),
            cls._difference_feature(
                name="home_attack_vs_away_defence",
                home_value=home_snapshot.attack_rating,
                away_value=away_snapshot.defence_rating,
                category="matchup",
                importance="critical",
                description=(
                    "Home attack rating minus away defence rating."
                ),
            ),
            cls._difference_feature(
                name="away_attack_vs_home_defence",
                home_value=away_snapshot.attack_rating,
                away_value=home_snapshot.defence_rating,
                category="matchup",
                importance="critical",
                description=(
                    "Away attack rating minus home defence rating."
                ),
            ),
            cls._difference_feature(
                name="goals_for_per_game_difference",
                home_value=home_snapshot.goals_for_per_game,
                away_value=away_snapshot.goals_for_per_game,
                category="goals_comparison",
                importance="high",
                description=(
                    "Home goals scored per game minus away goals scored per game."
                ),
            ),
            cls._difference_feature(
                name="goals_against_per_game_difference",
                home_value=home_snapshot.goals_against_per_game,
                away_value=away_snapshot.goals_against_per_game,
                category="goals_comparison",
                importance="high",
                description=(
                    "Home goals conceded per game minus away goals conceded per game."
                ),
            ),
            cls._difference_feature(
                name="home_scoring_vs_away_conceding",
                home_value=home_snapshot.home_goals_for_per_game,
                away_value=away_snapshot.away_goals_against_per_game,
                category="matchup",
                importance="critical",
                description=(
                    "Home venue scoring rate minus away venue conceding rate."
                ),
            ),
            cls._difference_feature(
                name="away_scoring_vs_home_conceding",
                home_value=away_snapshot.away_goals_for_per_game,
                away_value=home_snapshot.home_goals_against_per_game,
                category="matchup",
                importance="critical",
                description=(
                    "Away venue scoring rate minus home venue conceding rate."
                ),
            ),
            cls._difference_feature(
                name="clean_sheet_rate_difference",
                home_value=home_snapshot.clean_sheet_rate,
                away_value=away_snapshot.clean_sheet_rate,
                category="defence_comparison",
                importance="normal",
                description=(
                    "Home clean-sheet rate minus away clean-sheet rate."
                ),
            ),
            cls._difference_feature(
                name="failed_to_score_rate_difference",
                home_value=home_snapshot.failed_to_score_rate,
                away_value=away_snapshot.failed_to_score_rate,
                category="attack_comparison",
                importance="normal",
                description=(
                    "Home failed-to-score rate minus away failed-to-score rate."
                ),
            ),
            cls._average_feature(
                name="combined_btts_rate",
                first_value=home_snapshot.btts_rate,
                second_value=away_snapshot.btts_rate,
                category="goals_market",
                importance="high",
                description="Average BTTS rate of both teams.",
            ),
            cls._average_feature(
                name="combined_over_2_5_rate",
                first_value=home_snapshot.over_2_5_rate,
                second_value=away_snapshot.over_2_5_rate,
                category="goals_market",
                importance="high",
                description="Average over 2.5 goals rate of both teams.",
            ),
            cls._difference_feature(
                name="rest_days_difference",
                home_value=home_snapshot.days_since_last_match,
                away_value=away_snapshot.days_since_last_match,
                category="schedule",
                importance="normal",
                description=(
                    "Home rest days minus away rest days."
                ),
            ),
            cls._difference_feature(
                name="league_position_advantage",
                home_value=away_snapshot.current_position,
                away_value=home_snapshot.current_position,
                category="standing_comparison",
                importance="normal",
                description=(
                    "Positive value means home team has the better league position."
                ),
            ),
            cls._minimum_feature(
                name="minimum_data_completeness",
                first_value=home_snapshot.data_completeness,
                second_value=away_snapshot.data_completeness,
                category="data_quality",
                importance="high",
                description=(
                    "Lower data completeness value across both snapshots."
                ),
            ),
        ]

    @staticmethod
    def _difference_feature(
        *,
        name: str,
        home_value: Decimal | int | float | None,
        away_value: Decimal | int | float | None,
        category: str,
        importance: str,
        description: str,
    ) -> Feature:
        value = None

        if home_value is not None and away_value is not None:
            value = Decimal(str(home_value)) - Decimal(str(away_value))
            value = value.quantize(Decimal("0.0001"))

        return Feature(
            name=name,
            value=value,
            category=category,
            source="match_feature_builder",
            importance=importance,
            description=description,
        )

    @staticmethod
    def _average_feature(
        *,
        name: str,
        first_value: Decimal | int | float | None,
        second_value: Decimal | int | float | None,
        category: str,
        importance: str,
        description: str,
    ) -> Feature:
        value = None

        if first_value is not None and second_value is not None:
            value = (
                Decimal(str(first_value))
                + Decimal(str(second_value))
            ) / Decimal("2")

            value = value.quantize(Decimal("0.0001"))

        return Feature(
            name=name,
            value=value,
            category=category,
            source="match_feature_builder",
            importance=importance,
            description=description,
        )

    @staticmethod
    def _minimum_feature(
        *,
        name: str,
        first_value: Decimal | int | float | None,
        second_value: Decimal | int | float | None,
        category: str,
        importance: str,
        description: str,
    ) -> Feature:
        value = None

        if first_value is not None and second_value is not None:
            value = min(
                Decimal(str(first_value)),
                Decimal(str(second_value)),
            ).quantize(Decimal("0.0001"))

        return Feature(
            name=name,
            value=value,
            category=category,
            source="match_feature_builder",
            importance=importance,
            description=description,
        )

    @staticmethod
    def _validate_snapshots(
        *,
        home_snapshot: TeamSnapshot,
        away_snapshot: TeamSnapshot,
    ) -> None:
        if home_snapshot.team_id is None:
            raise ValueError("home_snapshot.team_id cannot be None.")

        if away_snapshot.team_id is None:
            raise ValueError("away_snapshot.team_id cannot be None.")

        if home_snapshot.team_id == away_snapshot.team_id:
            raise ValueError(
                "Home and away snapshots cannot belong to the same team."
            )

        if home_snapshot.competition_id is None:
            raise ValueError(
                "home_snapshot.competition_id cannot be None."
            )

        if away_snapshot.competition_id is None:
            raise ValueError(
                "away_snapshot.competition_id cannot be None."
            )

        if home_snapshot.competition_id != away_snapshot.competition_id:
            raise ValueError(
                "Home and away snapshots must belong to the same competition."
            )

        if home_snapshot.season_id is None:
            raise ValueError(
                "home_snapshot.season_id cannot be None."
            )

        if away_snapshot.season_id is None:
            raise ValueError(
                "away_snapshot.season_id cannot be None."
            )

        if home_snapshot.season_id != away_snapshot.season_id:
            raise ValueError(
                "Home and away snapshots must belong to the same season."
            )
