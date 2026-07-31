import {
  CalendarDays,
  RotateCcw,
  Search,
} from "lucide-react"

interface FilterOption {
  id: string
  name: string
}

interface FixtureFiltersProps {
  search: string
  status: string
  date: string
  competitionId: string
  teamId: string
  competitions: FilterOption[]
  teams: FilterOption[]
  onSearchChange: (value: string) => void
  onStatusChange: (value: string) => void
  onDateChange: (value: string) => void
  onCompetitionChange: (value: string) => void
  onTeamChange: (value: string) => void
  onReset: () => void
}

const inputClassName =
  "h-11 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"

export function FixtureFilters({
  search,
  status,
  date,
  competitionId,
  teamId,
  competitions,
  teams,
  onSearchChange,
  onStatusChange,
  onDateChange,
  onCompetitionChange,
  onTeamChange,
  onReset,
}: FixtureFiltersProps) {
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
      <div className="grid gap-4 lg:grid-cols-12">
        <div className="lg:col-span-4">
          <label className="mb-2 block text-xs font-semibold text-slate-400">
            البحث
          </label>

          <div className="relative">
            <Search className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />

            <input
              value={search}
              onChange={(event) =>
                onSearchChange(event.target.value)
              }
              placeholder="ابحث باسم فريق أو بطولة..."
              className={`${inputClassName} pr-10`}
            />
          </div>
        </div>

        <div className="lg:col-span-2">
          <label className="mb-2 block text-xs font-semibold text-slate-400">
            الحالة
          </label>

          <select
            value={status}
            onChange={(event) =>
              onStatusChange(event.target.value)
            }
            className={inputClassName}
          >
            <option value="">جميع الحالات</option>
            <option value="scheduled">مجدولة</option>
            <option value="live">مباشرة</option>
            <option value="finished">انتهت</option>
            <option value="postponed">مؤجلة</option>
            <option value="cancelled">ملغاة</option>
            <option value="suspended">متوقفة</option>
          </select>
        </div>

        <div className="lg:col-span-2">
          <label className="mb-2 block text-xs font-semibold text-slate-400">
            البطولة
          </label>

          <select
            value={competitionId}
            onChange={(event) =>
              onCompetitionChange(event.target.value)
            }
            className={inputClassName}
          >
            <option value="">جميع البطولات</option>

            {competitions.map((competition) => (
              <option
                key={competition.id}
                value={competition.id}
              >
                {competition.name}
              </option>
            ))}
          </select>
        </div>

        <div className="lg:col-span-2">
          <label className="mb-2 block text-xs font-semibold text-slate-400">
            الفريق
          </label>

          <select
            value={teamId}
            onChange={(event) =>
              onTeamChange(event.target.value)
            }
            className={inputClassName}
          >
            <option value="">جميع الفرق</option>

            {teams.map((team) => (
              <option key={team.id} value={team.id}>
                {team.name}
              </option>
            ))}
          </select>
        </div>

        <div className="lg:col-span-2">
          <label className="mb-2 block text-xs font-semibold text-slate-400">
            التاريخ
          </label>

          <div className="relative">
            <CalendarDays className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />

            <input
              type="date"
              value={date}
              onChange={(event) =>
                onDateChange(event.target.value)
              }
              className={`${inputClassName} pr-10`}
              dir="ltr"
            />
          </div>
        </div>
      </div>

      <div className="mt-4 flex justify-end">
        <button
          type="button"
          onClick={onReset}
          className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-4 text-sm font-semibold text-slate-200 transition hover:border-slate-600 hover:bg-slate-700"
        >
          <RotateCcw className="h-4 w-4" />
          إعادة ضبط الفلاتر
        </button>
      </div>
    </section>
  )
}
