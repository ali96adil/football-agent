from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from typing import Final

from app.domain.team_intelligence import TeamRatings, TeamStatistics


class RatingEngine:
    """
    Convert team statistics into normalized ratings from 0 to 100.

    The engine is intentionally pure:
    - no database access
    - no HTTP calls
    - deterministic output
    """

    MIN_RATING: Final[float] = 0.0
    MAX_RATING: Final[float] = 100.0
    NEUTRAL_RATING: Final[float] = 50.0

    @classmethod
    def calculate(
        cls,
        statistics: TeamStatistics,
    ) -> TeamRatings:
        attack_rating = cls._calculate_attack_rating(statistics)
        defence_rating = cls._calculate_defence_rating(statistics)
        form_rating = cls._calculate_form_rating(statistics)
        home_rating = cls._calculate_home_rating(statistics)
        away_rating = cls._calculate_away_rating(statistics)

        overall_rating = cls._calculate_overall_rating(
            attack_rating=attack_rating,
            defence_rating=defence_rating,
            form_rating=form_rating,
            home_rating=home_rating,
            away_rating=away_rating,
        )

        return TeamRatings(
            attack_rating=cls._round(attack_rating),
            defence_rating=cls._round(defence_rating),
            form_rating=cls._round(form_rating),
            home_rating=cls._round(home_rating),
            away_rating=cls._round(away_rating),
            overall_rating=cls._round(overall_rating),
            elo_rating=None,
        )

    @classmethod
    def _calculate_attack_rating(
        cls,
        statistics: TeamStatistics,
    ) -> float:
        if statistics.matches_played == 0:
            return cls.NEUTRAL_RATING

        goals_score = cls._normalize(
            float(statistics.goals_for_per_game),
            minimum=0.0,
            maximum=3.0,
        )

        scoring_reliability = (
            1.0 - float(statistics.failed_to_score_rate)
        ) * 100.0

        over_2_5_score = (
            float(statistics.over_2_5_rate) * 100.0
        )

        return cls._weighted_average(
            (
                (goals_score, 0.60),
                (scoring_reliability, 0.25),
                (over_2_5_score, 0.15),
            )
        )

    @classmethod
    def _calculate_defence_rating(
        cls,
        statistics: TeamStatistics,
    ) -> float:
        if statistics.matches_played == 0:
            return cls.NEUTRAL_RATING

        goals_conceded_penalty = cls._normalize(
            float(statistics.goals_against_per_game),
            minimum=0.0,
            maximum=3.0,
        )

        goals_conceded_score = 100.0 - goals_conceded_penalty

        clean_sheet_score = (
            float(statistics.clean_sheet_rate) * 100.0
        )

        btts_prevention_score = (
            1.0 - float(statistics.btts_rate)
        ) * 100.0

        return cls._weighted_average(
            (
                (goals_conceded_score, 0.60),
                (clean_sheet_score, 0.25),
                (btts_prevention_score, 0.15),
            )
        )

    @classmethod
    def _calculate_form_rating(
        cls,
        statistics: TeamStatistics,
    ) -> float:
        if statistics.matches_played == 0:
            return cls.NEUTRAL_RATING

        points_score = cls._normalize(
            float(statistics.points_per_game),
            minimum=0.0,
            maximum=3.0,
        )

        sequence_score = cls._calculate_sequence_score(
            statistics.form_sequence
        )

        return cls._weighted_average(
            (
                (points_score, 0.85),
                (sequence_score, 0.15),
            )
        )

    @classmethod
    def _calculate_home_rating(
        cls,
        statistics: TeamStatistics,
    ) -> float:
        if statistics.home.matches == 0:
            return cls.NEUTRAL_RATING

        points_score = cls._normalize(
            float(statistics.home.points_per_game),
            minimum=0.0,
            maximum=3.0,
        )

        goal_difference_per_game = (
            float(statistics.home.goals_for_per_game)
            - float(statistics.home.goals_against_per_game)
        )

        goal_difference_score = cls._normalize(
            goal_difference_per_game,
            minimum=-3.0,
            maximum=3.0,
        )

        return cls._weighted_average(
            (
                (points_score, 0.75),
                (goal_difference_score, 0.25),
            )
        )

    @classmethod
    def _calculate_away_rating(
        cls,
        statistics: TeamStatistics,
    ) -> float:
        if statistics.away.matches == 0:
            return cls.NEUTRAL_RATING

        points_score = cls._normalize(
            float(statistics.away.points_per_game),
            minimum=0.0,
            maximum=3.0,
        )

        goal_difference_per_game = (
            float(statistics.away.goals_for_per_game)
            - float(statistics.away.goals_against_per_game)
        )

        goal_difference_score = cls._normalize(
            goal_difference_per_game,
            minimum=-3.0,
            maximum=3.0,
        )

        return cls._weighted_average(
            (
                (points_score, 0.75),
                (goal_difference_score, 0.25),
            )
        )

    @classmethod
    def _calculate_overall_rating(
        cls,
        *,
        attack_rating: float,
        defence_rating: float,
        form_rating: float,
        home_rating: float,
        away_rating: float,
    ) -> float:
        return cls._weighted_average(
            (
                (attack_rating, 0.35),
                (defence_rating, 0.35),
                (form_rating, 0.20),
                (home_rating, 0.05),
                (away_rating, 0.05),
            )
        )

    @classmethod
    def _calculate_sequence_score(
        cls,
        form_sequence: str,
    ) -> float:
        """
        Calculate a recency-weighted form score.

        StatisticsEngine currently returns newest result first.
        For example: WWD means newest result is W.
        """

        sequence = [
            result.upper()
            for result in form_sequence
            if result.upper() in {"W", "D", "L"}
        ]

        if not sequence:
            return cls.NEUTRAL_RATING

        result_points = {
            "W": 3.0,
            "D": 1.0,
            "L": 0.0,
        }

        weighted_points = 0.0
        maximum_weighted_points = 0.0

        for index, result in enumerate(sequence):
            weight = float(len(sequence) - index)

            weighted_points += result_points[result] * weight
            maximum_weighted_points += 3.0 * weight

        if maximum_weighted_points == 0:
            return cls.NEUTRAL_RATING

        return cls._clamp(
            weighted_points
            / maximum_weighted_points
            * 100.0
        )

    @classmethod
    def _normalize(
        cls,
        value: float,
        *,
        minimum: float,
        maximum: float,
    ) -> float:
        if maximum <= minimum:
            raise ValueError(
                "maximum must be greater than minimum"
            )

        normalized = (
            (value - minimum)
            / (maximum - minimum)
            * 100.0
        )

        return cls._clamp(normalized)

    @classmethod
    def _weighted_average(
        cls,
        values: tuple[tuple[float, float], ...],
    ) -> float:
        total_weight = sum(weight for _, weight in values)

        if total_weight <= 0:
            raise ValueError(
                "Total rating weight must be greater than zero"
            )

        result = sum(
            cls._clamp(value) * weight
            for value, weight in values
        ) / total_weight

        return cls._clamp(result)

    @classmethod
    def _clamp(
        cls,
        value: float,
    ) -> float:
        return max(
            cls.MIN_RATING,
            min(cls.MAX_RATING, value),
        )

    @staticmethod
    def _round(
        value: float,
    ) -> float:
        return round(value, 4)