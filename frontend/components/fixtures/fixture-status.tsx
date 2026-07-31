import {
  isFinishedStatus,
  isLiveStatus,
  translateFixtureStatus,
} from "@/lib/fixture-format"

interface FixtureStatusProps {
  status: string
}

export function FixtureStatus({
  status,
}: FixtureStatusProps) {
  const normalizedStatus = status.toLowerCase()

  let className =
    "border-slate-600 bg-slate-800 text-slate-200"

  if (isLiveStatus(normalizedStatus)) {
    className =
      "border-red-500/40 bg-red-500/15 text-red-300"
  } else if (
    ["scheduled", "timed", "not_started"].includes(
      normalizedStatus,
    )
  ) {
    className =
      "border-amber-500/40 bg-amber-500/15 text-amber-300"
  } else if (isFinishedStatus(normalizedStatus)) {
    className =
      "border-slate-500/40 bg-slate-500/15 text-slate-300"
  } else if (normalizedStatus === "postponed") {
    className =
      "border-orange-500/40 bg-orange-500/15 text-orange-300"
  } else if (
    ["cancelled", "canceled", "abandoned"].includes(
      normalizedStatus,
    )
  ) {
    className =
      "border-rose-500/40 bg-rose-500/15 text-rose-300"
  } else if (normalizedStatus === "suspended") {
    className =
      "border-blue-500/40 bg-blue-500/15 text-blue-300"
  }

  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${className}`}
    >
      {isLiveStatus(normalizedStatus) && (
        <span className="ml-2 h-2 w-2 animate-pulse rounded-full bg-current" />
      )}

      {translateFixtureStatus(status)}
    </span>
  )
}
