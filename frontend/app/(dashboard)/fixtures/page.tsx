"use client"

import { useEffect, useMemo, useState } from "react"
import {
  AlertTriangle,
  CalendarRange,
  LoaderCircle,
} from "lucide-react"

import { FixtureCard } from "@/components/fixtures/fixture-card"
import { FixtureFilters } from "@/components/fixtures/fixture-filters"
import { FixturePagination } from "@/components/fixtures/fixture-pagination"
import { FixtureStats } from "@/components/fixtures/fixture-stats"
import { useFixtures } from "@/hooks/use-fixtures"
import {
  getAwayTeam,
  getCompetition,
  getHomeTeam,
  translateCompetition,
} from "@/lib/fixture-format"

const PAGE_SIZE = 20

export default function FixturesPage() {
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState("")
  const [search, setSearch] = useState("")
  const [status, setStatus] = useState("")
  const [date, setDate] = useState("")
  const [competitionId, setCompetitionId] =
    useState("")
  const [teamId, setTeamId] = useState("")

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 400)

    return () => window.clearTimeout(timeout)
  }, [searchInput])

  const fixturesQuery = useFixtures({
    page,
    page_size: PAGE_SIZE,
    search: search || undefined,
    status: status || undefined,
    date: date || undefined,
    competition_id: competitionId || undefined,
    team_id: teamId || undefined,
    sort: "upcoming",
  })

  const fixtures = useMemo(
    () => fixturesQuery.data?.items ?? [],
    [fixturesQuery.data?.items],
  )
  const total = fixturesQuery.data?.total ?? 0
  const totalPages =
    fixturesQuery.data?.total_pages ?? 1

  const competitions = useMemo(() => {
    const map = new Map<string, string>()

    fixtures.forEach((fixture) => {
      const competition = getCompetition(fixture)

      if (
        competition.id !== null &&
        competition.id !== undefined
      ) {
        map.set(
          String(competition.id),
          translateCompetition(competition.name),
        )
      }
    })

    if (
      competitionId &&
      !map.has(competitionId)
    ) {
      map.set(competitionId, "البطولة المحددة")
    }

    return Array.from(map, ([id, name]) => ({
      id,
      name,
    })).sort((a, b) =>
      a.name.localeCompare(b.name, "ar"),
    )
  }, [fixtures, competitionId])

  const teams = useMemo(() => {
    const map = new Map<string, string>()

    fixtures.forEach((fixture) => {
      const homeTeam = getHomeTeam(fixture)
      const awayTeam = getAwayTeam(fixture)

      if (
        homeTeam.id !== null &&
        homeTeam.id !== undefined
      ) {
        map.set(String(homeTeam.id), homeTeam.name)
      }

      if (
        awayTeam.id !== null &&
        awayTeam.id !== undefined
      ) {
        map.set(String(awayTeam.id), awayTeam.name)
      }
    })

    if (teamId && !map.has(teamId)) {
      map.set(teamId, "الفريق المحدد")
    }

    return Array.from(map, ([id, name]) => ({
      id,
      name,
    })).sort((a, b) =>
      a.name.localeCompare(b.name),
    )
  }, [fixtures, teamId])

  function resetFilters() {
    setSearchInput("")
    setSearch("")
    setStatus("")
    setDate("")
    setCompetitionId("")
    setTeamId("")
    setPage(1)
  }

  function changePage(newPage: number) {
    setPage(newPage)

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    })
  }

  return (
    <main
      className="min-h-screen bg-slate-950 text-slate-100"
      dir="rtl"
    >
      <div className="mx-auto w-full max-w-[1600px] space-y-6 p-4 sm:p-6 lg:p-8">
        <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-blue-300">
              <CalendarRange className="h-4 w-4" />
              مركز المباريات
            </div>

            <h1 className="text-3xl font-black tracking-tight text-white">
              المباريات
            </h1>

            <p className="mt-2 text-sm text-slate-400">
              البحث ومتابعة مواعيد المباريات وحالاتها
              والبطولات المرتبطة بها.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 px-5 py-3">
            <p className="text-xs font-medium text-slate-500">
              إجمالي المباريات
            </p>

            <p className="mt-1 text-2xl font-black text-white">
              {total.toLocaleString("en-US")}
            </p>
          </div>
        </header>


        <FixtureStats   
          total={total}
          today={
           fixtures.filter((f) => {
              const fixtureDate =
                f.kickoff_at ??
                f.utc_date ??
                f.date ??
                f.scheduled_at

              if (!fixtureDate) return false

              return (
                new Date(fixtureDate).toISOString().slice(0, 10) ===
                new Date().toISOString().slice(0, 10)
              )
            }).length
          }
          live={
            fixtures.filter((f) =>
              ["live", "inplay", "1h", "2h", "ht"].includes(
                f.status.toLowerCase()
              )
            ).length
          }
          competitions={competitions.length}
        />

        <FixtureFilters
          search={searchInput}
          status={status}
          date={date}
          competitionId={competitionId}
          teamId={teamId}
          competitions={competitions}
          teams={teams}
          onSearchChange={setSearchInput}
          onStatusChange={(value) => {
            setStatus(value)
            setPage(1)
          }}
          onDateChange={(value) => {
            setDate(value)
            setPage(1)
          }}
          onCompetitionChange={(value) => {
            setCompetitionId(value)
            setPage(1)
          }}
          onTeamChange={(value) => {
            setTeamId(value)
            setPage(1)
          }}
          onReset={resetFilters}
        />

        {fixturesQuery.isLoading ? (
          <div className="flex min-h-72 flex-col items-center justify-center rounded-2xl border border-slate-800 bg-slate-900/60">
            <LoaderCircle className="h-10 w-10 animate-spin text-blue-400" />
            <p className="mt-4 text-sm text-slate-400">
              جارٍ تحميل المباريات...
            </p>
          </div>
        ) : fixturesQuery.isError ? (
          <div className="flex min-h-72 flex-col items-center justify-center rounded-2xl border border-red-500/30 bg-red-500/5 p-6 text-center">
            <AlertTriangle className="h-10 w-10 text-red-400" />

            <h2 className="mt-4 text-lg font-bold text-white">
              تعذر تحميل المباريات
            </h2>

            <p className="mt-2 max-w-xl text-sm text-slate-400">
              {fixturesQuery.error instanceof Error
                ? fixturesQuery.error.message
                : "حدث خطأ غير متوقع أثناء الاتصال بالخادم."}
            </p>

            <button
              type="button"
              onClick={() => fixturesQuery.refetch()}
              className="mt-5 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500"
            >
              إعادة المحاولة
            </button>
          </div>
        ) : fixtures.length === 0 ? (
          <div className="flex min-h-72 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-700 bg-slate-900/40 p-6 text-center">
            <CalendarRange className="h-10 w-10 text-slate-500" />

            <h2 className="mt-4 text-lg font-bold text-white">
              لا توجد مباريات مطابقة
            </h2>

            <p className="mt-2 text-sm text-slate-400">
              جرّب تغيير البحث أو إزالة بعض الفلاتر.
            </p>

            <button
              type="button"
              onClick={resetFilters}
              className="mt-5 rounded-xl border border-slate-700 bg-slate-800 px-5 py-2.5 text-sm font-semibold text-slate-200 hover:bg-slate-700"
            >
              مسح جميع الفلاتر
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm text-slate-400">
                عرض{" "}
                <strong className="text-slate-200">
                  {fixtures.length}
                </strong>{" "}
                مباراة في الصفحة الحالية
              </p>

              {fixturesQuery.isFetching && (
                <div className="flex items-center gap-2 text-xs text-blue-300">
                  <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                  جارٍ تحديث النتائج
                </div>
              )}
            </div>

            <section className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
              {fixtures.map((fixture) => (
                <FixtureCard
                  key={fixture.id}
                  fixture={fixture}
                />
              ))}
            </section>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <FixturePagination
                page={page}
                totalPages={totalPages}
                onPageChange={changePage}
              />
            </div>
          </>
        )}
      </div>
    </main>
  )
}
