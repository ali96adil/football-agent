from __future__ import annotations

from decimal import Decimal

from app.feature_engineering.domain.feature_vector import FeatureVector
from app.prediction.domain.expected_goals import ExpectedGoals


class ExpectedGoalsEngine:
    """
    Convert a match FeatureVector into expected-goals values.

    Version 1 uses venue scoring and conceding rates as the base,
    then applies bounded rating, form and Elo adjustments.
    """

    MODEL_VERSION = "expected-goals-v1"

    DEFAULT_HOME_GOALS = Decimal("1.45")
    DEFAULT_AWAY_GOALS = Decimal("1.15")

    MIN_EXPECTED_GOALS = Decimal("0.10")
    MAX_EXPECTED_GOALS = Decimal("4.50")

    @classmethod
    def calculate(
        cls,
        feature_vector: FeatureVector,
    ) -> ExpectedGoals:
        home_base = cls._mean_available(
            feature_vector.get_value(
                "home_venue_goals_for_per_game"
            ),
            feature_vector.get_value(
                "away_venue_goals_against_per_game"
            ),
            default=cls.DEFAULT_HOME_GOALS,
        )

        away_base = cls._mean_available(
            feature_vector.get_value(
                "away_venue_goals_for_per_game"
            ),
            feature_vector.get_value(
                "home_venue_goals_against_per_game"
            ),
            default=cls.DEFAULT_AWAY_GOALS,
        )

        home_multiplier = Decimal("1")
        away_multiplier = Decimal("1")

        matchup_home = cls._decimal_or_zero(
            feature_vector.get_value(
                "home_attack_vs_away_defence"
            )
        )

        matchup_away = cls._decimal_or_zero(
            feature_vector.get_value(
                "away_attack_vs_home_defence"
            )
        )

        venue_difference = cls._decimal_or_zero(
            feature_vector.get_value(
                "venue_rating_difference"
            )
        )

        form_difference = cls._decimal_or_zero(
            feature_vector.get_value(
                "form_rating_difference"
            )
        )

        elo_difference = cls._decimal_or_zero(
            feature_vector.get_value(
                "elo_rating_difference"
            )
        )

        home_multiplier += cls._bounded_adjustment(
            matchup_home,
            divisor=Decimal("200"),
            limit=Decimal("0.25"),
        )

        away_multiplier += cls._bounded_adjustment(
            matchup_away,
            divisor=Decimal("200"),
            limit=Decimal("0.25"),
        )

        venue_adjustment = cls._bounded_adjustment(
            venue_difference,
            divisor=Decimal("300"),
            limit=Decimal("0.15"),
        )

        home_multiplier += venue_adjustment
        away_multiplier -= venue_adjustment

        form_adjustment = cls._bounded_adjustment(
            form_difference,
            divisor=Decimal("400"),
            limit=Decimal("0.10"),
        )

        home_multiplier += form_adjustment
        away_multiplier -= form_adjustment

        elo_adjustment = cls._bounded_adjustment(
            elo_difference,
            divisor=Decimal("2500"),
            limit=Decimal("0.12"),
        )

        home_multiplier += elo_adjustment
        away_multiplier -= elo_adjustment

        home_expected = cls._clamp(
            home_base * home_multiplier,
            minimum=cls.MIN_EXPECTED_GOALS,
            maximum=cls.MAX_EXPECTED_GOALS,
        )

        away_expected = cls._clamp(
            away_base * away_multiplier,
            minimum=cls.MIN_EXPECTED_GOALS,
            maximum=cls.MAX_EXPECTED_GOALS,
        )

        confidence = cls._calculate_confidence(
            feature_vector
        )

        return ExpectedGoals(
            home=home_expected.quantize(
                Decimal("0.0001")
            ),
            away=away_expected.quantize(
                Decimal("0.0001")
            ),
            model_version=cls.MODEL_VERSION,
            confidence=confidence,
        )

    @classmethod
    def _calculate_confidence(
        cls,
        feature_vector: FeatureVector,
    ) -> Decimal:
        completeness = cls._decimal_or_none(
            feature_vector.get_value(
                "minimum_data_completeness"
            )
        )

        if completeness is None:
            return Decimal("0.5000")

        return cls._clamp(
            completeness,
            minimum=Decimal("0"),
            maximum=Decimal("1"),
        ).quantize(Decimal("0.0001"))

    @classmethod
    def _mean_available(
        cls,
        first_value,
        second_value,
        *,
        default: Decimal,
    ) -> Decimal:
        values = [
            value
            for value in (
                cls._decimal_or_none(first_value),
                cls._decimal_or_none(second_value),
            )
            if value is not None
        ]

        if not values:
            return default

        return (
            sum(values, Decimal("0"))
            / Decimal(len(values))
        )

    @staticmethod
    def _bounded_adjustment(
        value: Decimal,
        *,
        divisor: Decimal,
        limit: Decimal,
    ) -> Decimal:
        adjustment = value / divisor

        return max(
            -limit,
            min(limit, adjustment),
        )

    @staticmethod
    def _decimal_or_none(value) -> Decimal | None:
        if value is None:
            return None

        return Decimal(str(value))

    @classmethod
    def _decimal_or_zero(cls, value) -> Decimal:
        decimal_value = cls._decimal_or_none(value)

        if decimal_value is None:
            return Decimal("0")

        return decimal_value

    @staticmethod
    def _clamp(
        value: Decimal,
        *,
        minimum: Decimal,
        maximum: Decimal,
    ) -> Decimal:
        return max(
            minimum,
            min(maximum, value),
        )
