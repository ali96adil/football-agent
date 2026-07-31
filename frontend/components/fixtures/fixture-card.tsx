import {
  CalendarDays,
  Clock3,
  Trophy,
} from "lucide-react"

import { FixtureStatus } from "@/components/fixtures/fixture-status"

import {
  formatFixtureDate,
  formatFixtureTime,
  getAwayTeam,
  getCompetition,
  getFixtureDateValue,
  getFixtureScore,
  getHomeTeam,
  isFinishedStatus,
  isLiveStatus,
  translateCompetition,
} from "@/lib/fixture-format"

import type {
  Fixture,
  FixtureTeam,
} from "@/types/fixtures"

interface FixtureCardProps {
  fixture: Fixture
}

function TeamLogo({
  team,
}: {
  team: FixtureTeam
}) {
  const logo =
    team.logo ??
    team.crest ??
    null

  if (logo) {
    return (
      <img
        src={logo}
        alt={team.name}
        className="h-14 w-14 object-contain"
        loading="lazy"
      />
    )
  }

  const letter =
    team.name.trim().charAt(0).toUpperCase()

  return (
    <div className="flex h-14 w-14 items-center justify-center rounded-full border border-slate-700 bg-slate-800 text-xl font-bold text-slate-300">
      {letter || "؟"}
    </div>
  )
}

export function FixtureCard({
  fixture,
}: FixtureCardProps) {
  const competition = getCompetition(fixture)
  const homeTeam = getHomeTeam(fixture)
  const awayTeam = getAwayTeam(fixture)

  const fixtureDate =
    getFixtureDateValue(fixture)

  const score =
    getFixtureScore(fixture)

  const showScore =
    isFinishedStatus(fixture.status) ||
    isLiveStatus(fixture.status) ||
    score.home !== null ||
    score.away !== null

  return (
    <article className="group overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-slate-700 hover:shadow-xl">

      <header className="flex items-center justify-between gap-3 border-b border-slate-800 px-5 py-4">

        <div className="flex min-w-0 items-center gap-3">

          {competition.logo ? (
            <img
              src={competition.logo}
              alt={competition.name}
              className="h-8 w-8 shrink-0 object-contain"
              loading="lazy"
            />
          ) : (
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800">
              <Trophy className="h-4 w-4 text-amber-300" />
            </div>
          )}

          <p
            className="truncate text-sm font-semibold text-slate-200"
            title={competition.name}
          >
            {translateCompetition(
              competition.name
            )}
          </p>

        </div>

        <FixtureStatus
          status={fixture.status}
        />

      </header>

      <div className="px-5 py-6">

        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4">

          <div className="flex flex-col items-center gap-3 text-center">

            <TeamLogo
              team={homeTeam}
            />

            <p
              className="line-clamp-2 min-h-10 text-sm font-semibold text-white"
              title={homeTeam.name}
            >
              {homeTeam.name}
            </p>

          </div>

          <div className="flex min-w-16 flex-col items-center justify-center">

            {showScore ? (
              <div
                dir="ltr"
                className="text-2xl font-black text-white"
              >
                {score.home ?? "–"} : {score.away ?? "–"}
              </div>
            ) : (
              <div className="rounded-full border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-bold text-slate-400">
                VS
              </div>
            )}

          </div>

          <div className="flex flex-col items-center gap-3 text-center">

            <TeamLogo
              team={awayTeam}
            />

            <p
              className="line-clamp-2 min-h-10 text-sm font-semibold text-white"
              title={awayTeam.name}
            >
              {awayTeam.name}
            </p>

          </div>

        </div>

      </div>

      <footer className="grid grid-cols-2 border-t border-slate-800 bg-slate-950/40">

        <div className="flex items-center justify-center gap-2 border-l border-slate-800 px-3 py-3 text-sm text-slate-300">

          <CalendarDays className="h-4 w-4 text-slate-500" />

          <span dir="ltr">
            {formatFixtureDate(
              fixtureDate
            )}
          </span>

        </div>

        <div className="flex items-center justify-center gap-2 px-3 py-3 text-sm text-slate-300">

          <Clock3 className="h-4 w-4 text-slate-500" />

          <span>
            {formatFixtureTime(
              fixtureDate
            )}
          </span>

        </div>

      </footer>

    </article>
  )
}