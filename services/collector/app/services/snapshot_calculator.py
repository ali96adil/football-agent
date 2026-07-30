from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.models.historical_match import HistoricalMatch
from app.models.snapshot_metrics import SnapshotMetrics


class SnapshotCalculator:

    def calculate(
        self,
        *,
        matches: list[HistoricalMatch],
        expected_window_size: int,
    ) -> SnapshotMetrics:

        played = len(matches)

        wins = sum(m.won for m in matches)
        draws = sum(m.drawn for m in matches)
        losses = sum(m.lost for m in matches)

        points = wins * 3 + draws

        goals_for = sum(m.goals_for for m in matches)
        goals_against = sum(m.goals_against for m in matches)

        clean_sheets = sum(m.clean_sheet for m in matches)
        failed_to_score = sum(m.failed_to_score for m in matches)
        btts_count = sum(m.both_teams_scored for m in matches)
        over_2_5_count = sum(m.over_2_5 for m in matches)

        home = [m for m in matches if m.is_home]
        away = [m for m in matches if not m.is_home]

        home_wins = sum(m.won for m in home)
        home_draws = sum(m.drawn for m in home)
        home_losses = sum(m.lost for m in home)

        away_wins = sum(m.won for m in away)
        away_draws = sum(m.drawn for m in away)
        away_losses = sum(m.lost for m in away)

        home_points = home_wins * 3 + home_draws
        away_points = away_wins * 3 + away_draws

        form = "".join(
            "W" if m.won else
            "D" if m.drawn else
            "L"
            for m in matches
        )

        def rate(value: int) -> Decimal:
            if played == 0:
                return Decimal("0")

            return (
                Decimal(value)
                / Decimal(played)
            ).quantize(
                Decimal("0.001"),
                rounding=ROUND_HALF_UP,
            )

        def average(value: int) -> Decimal:
            if played == 0:
                return Decimal("0")

            return (
                Decimal(value)
                / Decimal(played)
            ).quantize(
                Decimal("0.001"),
                rounding=ROUND_HALF_UP,
            )

        completeness = Decimal("0")

        if expected_window_size > 0:
            completeness = (
                Decimal(played)
                / Decimal(expected_window_size)
            ).quantize(
                Decimal("0.001"),
                rounding=ROUND_HALF_UP,
            )

        return SnapshotMetrics(
            matches_played=played,
            wins=wins,
            draws=draws,
            losses=losses,
            points=points,
            goals_for=goals_for,
            goals_against=goals_against,
            goal_difference=goals_for - goals_against,
            clean_sheets=clean_sheets,
            failed_to_score=failed_to_score,
            btts_count=btts_count,
            over_2_5_count=over_2_5_count,
            home_matches=len(home),
            home_wins=home_wins,
            home_draws=home_draws,
            home_losses=home_losses,
            home_points=home_points,
            away_matches=len(away),
            away_wins=away_wins,
            away_draws=away_draws,
            away_losses=away_losses,
            away_points=away_points,
            form_sequence=form,
            points_per_game=average(points),
            goals_for_per_game=average(goals_for),
            goals_against_per_game=average(goals_against),
            clean_sheet_rate=rate(clean_sheets),
            failed_to_score_rate=rate(failed_to_score),
            btts_rate=rate(btts_count),
            over_2_5_rate=rate(over_2_5_count),
            data_completeness=completeness,
        )