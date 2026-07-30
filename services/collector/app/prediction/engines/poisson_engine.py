from __future__ import annotations

import math
from decimal import Decimal

from app.prediction.domain.expected_goals import ExpectedGoals
from app.prediction.domain.match_prediction import MatchPrediction
from app.prediction.domain.score_probability import ScoreProbability


class PoissonEngine:
    """
    Convert expected goals into football score and market probabilities.
    """

    MODEL_VERSION = "poisson-v1"
    DEFAULT_MAX_GOALS = 8
    DEFAULT_TOP_SCORES = 5

    @classmethod
    def calculate(
        cls,
        expected_goals: ExpectedGoals,
        *,
        max_goals: int = DEFAULT_MAX_GOALS,
        top_scores: int = DEFAULT_TOP_SCORES,
    ) -> MatchPrediction:
        if max_goals < 1:
            raise ValueError(
                "max_goals must be greater than zero."
            )

        if top_scores < 1:
            raise ValueError(
                "top_scores must be greater than zero."
            )

        score_probabilities: list[ScoreProbability] = []

        home_win = Decimal("0")
        draw = Decimal("0")
        away_win = Decimal("0")
        btts_yes = Decimal("0")
        over_2_5 = Decimal("0")
        under_2_5 = Decimal("0")

        for home_goals in range(max_goals + 1):
            home_probability = cls._poisson_probability(
                goals=home_goals,
                expected_goals=expected_goals.home,
            )

            for away_goals in range(max_goals + 1):
                away_probability = cls._poisson_probability(
                    goals=away_goals,
                    expected_goals=expected_goals.away,
                )

                probability = (
                    home_probability * away_probability
                )

                score = ScoreProbability(
                    home_goals=home_goals,
                    away_goals=away_goals,
                    probability=probability,
                )

                score_probabilities.append(score)

                if home_goals > away_goals:
                    home_win += probability
                elif home_goals == away_goals:
                    draw += probability
                else:
                    away_win += probability

                if home_goals > 0 and away_goals > 0:
                    btts_yes += probability

                if home_goals + away_goals >= 3:
                    over_2_5 += probability
                else:
                    under_2_5 += probability

        total_probability = (
            home_win + draw + away_win
        )

        if total_probability <= Decimal("0"):
            raise ValueError(
                "Calculated probability mass is zero."
            )

        home_win = cls._normalise(
            home_win,
            total_probability,
        )

        draw = cls._normalise(
            draw,
            total_probability,
        )

        away_win = cls._normalise(
            away_win,
            total_probability,
        )

        btts_yes = cls._normalise(
            btts_yes,
            total_probability,
        )

        over_2_5 = cls._normalise(
            over_2_5,
            total_probability,
        )

        under_2_5 = cls._normalise(
            under_2_5,
            total_probability,
        )

        most_likely_scores = tuple(
            sorted(
                score_probabilities,
                key=lambda score: score.probability,
                reverse=True,
            )[:top_scores]
        )

        return MatchPrediction(
            expected_goals=expected_goals,
            home_win_probability=home_win,
            draw_probability=draw,
            away_win_probability=away_win,
            btts_yes_probability=btts_yes,
            over_2_5_probability=over_2_5,
            under_2_5_probability=under_2_5,
            most_likely_scores=most_likely_scores,
            model_version=cls.MODEL_VERSION,
        )

    @staticmethod
    def _poisson_probability(
        *,
        goals: int,
        expected_goals: Decimal,
    ) -> Decimal:
        expected = float(expected_goals)

        probability = (
            math.exp(-expected)
            * (expected ** goals)
            / math.factorial(goals)
        )

        return Decimal(
            str(probability)
        )

    @staticmethod
    def _normalise(
        value: Decimal,
        total: Decimal,
    ) -> Decimal:
        return (
            value / total
        ).quantize(Decimal("0.0001"))
