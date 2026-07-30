from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.team_intelligence import (
    CompletedFixture,
    TeamStatistics,
    VenueStatistics,
)


@dataclass(slots=True)
class _MutableVenueStatistics:
    matches: int = 0

    wins: int = 0
    draws: int = 0
    losses: int = 0

    points: int = 0

    goals_for: int = 0
    goals_against: int = 0

    def register(
        self,
        *,
        goals_for: int,
        goals_against: int,
    ) -> str:
        self.matches += 1
        self.goals_for += goals_for
        self.goals_against += goals_against

        if goals_for > goals_against:
            self.wins += 1
            self.points += 3
            return "W"

        if goals_for == goals_against:
            self.draws += 1
            self.points += 1
            return "D"

        self.losses += 1
        return "L"

    def freeze(self) -> VenueStatistics:
        return VenueStatistics(
            matches=self.matches,
            wins=self.wins,
            draws=self.draws,
            losses=self.losses,
            points=self.points,
            goals_for=self.goals_for,
            goals_against=self.goals_against,
        )


class StatisticsEngine:
    """
    Pure statistics calculator.

    It has no database, HTTP or provider dependencies.
    """

    @staticmethod
    def calculate(
        *,
        team_id: UUID,
        fixtures: list[CompletedFixture],
        window_size: int,
    ) -> TeamStatistics:
        if window_size <= 0:
            raise ValueError("window_size must be greater than zero.")

        relevant_fixtures = [
            fixture
            for fixture in fixtures
            if team_id in (
                fixture.home_team_id,
                fixture.away_team_id,
            )
        ]

        # Always select the newest N completed fixtures.
        selected = sorted(
            relevant_fixtures,
            key=lambda fixture: fixture.kickoff_at,
            reverse=True,
        )[:window_size]

        # Form sequence is stored oldest -> newest, such as WDLWW.
        selected = list(reversed(selected))

        home = _MutableVenueStatistics()
        away = _MutableVenueStatistics()

        wins = 0
        draws = 0
        losses = 0
        points = 0

        goals_for_total = 0
        goals_against_total = 0

        clean_sheets = 0
        failed_to_score = 0
        btts_count = 0
        over_2_5_count = 0

        form: list[str] = []
        fixture_ids: list[UUID] = []

        for fixture in selected:
            is_home = fixture.home_team_id == team_id

            if is_home:
                goals_for = fixture.home_score
                goals_against = fixture.away_score

                result = home.register(
                    goals_for=goals_for,
                    goals_against=goals_against,
                )
            else:
                goals_for = fixture.away_score
                goals_against = fixture.home_score

                result = away.register(
                    goals_for=goals_for,
                    goals_against=goals_against,
                )

            if result == "W":
                wins += 1
                points += 3
            elif result == "D":
                draws += 1
                points += 1
            else:
                losses += 1

            goals_for_total += goals_for
            goals_against_total += goals_against

            if goals_against == 0:
                clean_sheets += 1

            if goals_for == 0:
                failed_to_score += 1

            if goals_for > 0 and goals_against > 0:
                btts_count += 1

            if goals_for + goals_against > 2:
                over_2_5_count += 1

            form.append(result)
            fixture_ids.append(fixture.fixture_id)

        last_match_at = (
            max(fixture.kickoff_at for fixture in selected)
            if selected
            else None
        )

        return TeamStatistics(
            team_id=team_id,
            window_size=window_size,
            matches_played=len(selected),
            wins=wins,
            draws=draws,
            losses=losses,
            points=points,
            goals_for=goals_for_total,
            goals_against=goals_against_total,
            clean_sheets=clean_sheets,
            failed_to_score=failed_to_score,
            btts_count=btts_count,
            over_2_5_count=over_2_5_count,
            home=home.freeze(),
            away=away.freeze(),
            form_sequence="".join(form),
            fixture_ids=tuple(fixture_ids),
            last_match_at=last_match_at,
        )