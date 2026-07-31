import type {
  Fixture,
  FixtureCompetition,
  FixtureTeam,
} from "@/types/fixtures"

const competitionTranslations: Record<string, string> = {
  "Premier League": "الدوري الإنجليزي الممتاز",
  "La Liga": "الدوري الإسباني",
  "Serie A": "الدوري الإيطالي",
  Bundesliga: "الدوري الألماني",
  "Ligue 1": "الدوري الفرنسي",
  Eredivisie: "الدوري الهولندي",
  "Primeira Liga": "الدوري البرتغالي",
  "UEFA Champions League": "دوري أبطال أوروبا",
  "Champions League": "دوري أبطال أوروبا",
  "UEFA Europa League": "الدوري الأوروبي",
  "Europa League": "الدوري الأوروبي",
  "UEFA Conference League": "دوري المؤتمر الأوروبي",
  "Copa Libertadores": "كوبا ليبرتادوريس",
  "Campeonato Brasileiro Série A": "الدوري البرازيلي",
  "FIFA World Cup": "كأس العالم",
  "World Cup": "كأس العالم",
  "AFC Champions League": "دوري أبطال آسيا",
  "Saudi Pro League": "الدوري السعودي للمحترفين",
}

const statusTranslations: Record<string, string> = {
  scheduled: "مجدولة",
  timed: "مجدولة",
  not_started: "لم تبدأ",
  live: "مباشرة",
  in_play: "مباشرة",
  first_half: "الشوط الأول",
  second_half: "الشوط الثاني",
  halftime: "بين الشوطين",
  half_time: "بين الشوطين",
  paused: "متوقفة مؤقتًا",
  finished: "انتهت",
  full_time: "انتهت",
  after_extra_time: "انتهت بعد التمديد",
  penalties: "ركلات ترجيح",
  postponed: "مؤجلة",
  cancelled: "ملغاة",
  canceled: "ملغاة",
  suspended: "متوقفة",
  abandoned: "أُلغيت أثناء اللعب",
}

export function translateCompetition(name?: string | null) {
  if (!name) return "بطولة غير محددة"
  return competitionTranslations[name] ?? name
}

export function translateFixtureStatus(status?: string | null) {
  if (!status) return "غير معروفة"

  const normalizedStatus = status.toLowerCase().trim()
  return statusTranslations[normalizedStatus] ?? status
}

export function getFixtureDateValue(fixture: Fixture) {
  return (
    fixture.kickoff_at ??
    fixture.utc_date ??
    fixture.scheduled_at ??
    fixture.date ??
    null
  )
}

export function formatFixtureDate(value?: string | null) {
  if (!value) return "—"

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value.slice(0, 10)
  }

  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")

  return `${year}-${month}-${day}`
}

export function formatFixtureTime(value?: string | null) {
  if (!value) return "—"

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return "—"
  }

  return new Intl.DateTimeFormat("ar-IQ", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(date)
}

export function getCompetition(fixture: Fixture): FixtureCompetition {
  return {
    id: fixture.competition?.id ?? fixture.competition_id,
    name:
      fixture.competition?.name ??
      fixture.competition_name ??
      "بطولة غير محددة",
    logo:
      fixture.competition?.logo ??
      fixture.competition?.emblem ??
      fixture.competition_logo,
  }
}

export function getHomeTeam(fixture: Fixture): FixtureTeam {
  return {
    id: fixture.home_team?.id ?? fixture.home_team_id,
    name:
      fixture.home_team?.name ??
      fixture.home_team_name ??
      "الفريق المضيف",
    short_name: fixture.home_team?.short_name,
    logo:
      fixture.home_team?.logo ??
      fixture.home_team?.crest ??
      fixture.home_team?.crest_url ??
      fixture.home_team_logo,
  }
}

export function getAwayTeam(fixture: Fixture): FixtureTeam {
  return {
    id: fixture.away_team?.id ?? fixture.away_team_id,
    name:
      fixture.away_team?.name ??
      fixture.away_team_name ??
      "الفريق الضيف",
    short_name: fixture.away_team?.short_name,
    logo:
      fixture.away_team?.logo ??
      fixture.away_team?.crest ??
      fixture.away_team?.crest_url ??
      fixture.away_team_logo,
  }
}

export function getFixtureScore(fixture: Fixture) {
  return {
    home:
      fixture.home_score ??
      fixture.score_home ??
      null,
    away:
      fixture.away_score ??
      fixture.score_away ??
      null,
  }
}

export function isFinishedStatus(status?: string | null) {
  const value = status?.toLowerCase() ?? ""

  return [
    "finished",
    "full_time",
    "after_extra_time",
    "penalties",
  ].includes(value)
}

export function isLiveStatus(status?: string | null) {
  const value = status?.toLowerCase() ?? ""

  return [
    "live",
    "in_play",
    "first_half",
    "second_half",
    "halftime",
    "half_time",
    "paused",
  ].includes(value)
}
