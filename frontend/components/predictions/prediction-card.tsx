import Image from "next/image";

import { Prediction } from "@/types/prediction";
import { ProbabilityBar } from "./probability-bar";

type PredictionView = "upcoming" | "completed";

interface PredictionCardProps {
  prediction: Prediction;
  view: PredictionView;
}

function getTeamName(
  name: string,
  shortName?: string,
): string {
  return shortName || name;
}

function getOutcomeLabel(outcome?: string | null): string {
  switch (outcome) {
    case "home_win":
      return "Home Win";

    case "away_win":
      return "Away Win";

    case "draw":
      return "Draw";

    default:
      return outcome?.replaceAll("_", " ") || "Unknown";
  }
}

function getPredictedTeamName(
  prediction: Prediction,
): string {
  if (prediction.predicted_outcome === "home_win") {
    return getTeamName(
      prediction.home_team.name,
      prediction.home_team.short_name,
    );
  }

  if (prediction.predicted_outcome === "away_win") {
    return getTeamName(
      prediction.away_team.name,
      prediction.away_team.short_name,
    );
  }

  return "Draw";
}

function formatKickoff(kickoffAt: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Baghdad",
  }).format(new Date(kickoffAt));
}

function TeamLogo({
  name,
  logoUrl,
}: {
  name: string;
  logoUrl?: string;
}) {
  if (!logoUrl) {
    return (
      <div className="flex h-14 w-14 items-center justify-center rounded-full border bg-muted text-lg font-bold">
        {name.charAt(0).toUpperCase()}
      </div>
    );
  }

  return (
    <div className="relative h-14 w-14 shrink-0">
      <Image
        src={logoUrl}
        alt={`${name} logo`}
        fill
        sizes="56px"
        className="object-contain"
      />
    </div>
  );
}

function EvaluationBadge({
  correct,
  successText,
  failureText,
}: {
  correct?: boolean | null;
  successText: string;
  failureText: string;
}) {
  if (correct === null || correct === undefined) {
    return null;
  }

  return (
    <span
      className={[
        "inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold",
        correct
          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
          : "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-400",
      ].join(" ")}
    >
      {correct ? `✓ ${successText}` : `✕ ${failureText}`}
    </span>
  );
}

export function PredictionCard({
  prediction,
  view,
}: PredictionCardProps) {
  const homeTeamName = getTeamName(
    prediction.home_team.name,
    prediction.home_team.short_name,
  );

  const awayTeamName = getTeamName(
    prediction.away_team.name,
    prediction.away_team.short_name,
  );

  const predictedTeamName =
    getPredictedTeamName(prediction);

  const isCompleted =
    view === "completed" &&
    prediction.result_confirmed === true;

  const hasActualScore =
    prediction.actual_home_goals !== null &&
    prediction.actual_home_goals !== undefined &&
    prediction.actual_away_goals !== null &&
    prediction.actual_away_goals !== undefined;

  return (
    <article className="overflow-hidden rounded-2xl border bg-card shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md">
      <div className="border-b bg-muted/20 px-5 py-4 sm:px-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-sm font-semibold">
              {prediction.competition.name}
            </div>

            {prediction.competition.country_code && (
              <div className="mt-1 text-xs uppercase tracking-wide text-muted-foreground">
                {prediction.competition.country_code}
              </div>
            )}
          </div>

          <time className="text-sm text-muted-foreground">
            {formatKickoff(prediction.kickoff_at)}
          </time>
        </div>
      </div>

      <div className="p-5 sm:p-6">
        {/*
          dir="ltr" مهم:
          يمنع انعكاس Home وAway والأرقام داخل الصفحة العربية.
        */}
        <div
          dir="ltr"
          className="grid grid-cols-[1fr_auto_1fr] items-center gap-4"
        >
          <div className="flex min-w-0 flex-col items-center gap-3 text-center">
            <TeamLogo
              name={prediction.home_team.name}
              logoUrl={prediction.home_team.logo_url}
            />

            <div className="min-w-0">
              <div
                dir="auto"
                className="truncate font-semibold"
              >
                {homeTeamName}
              </div>

              <div className="mt-1 text-xs text-muted-foreground">
                Home
              </div>
            </div>
          </div>

          <div className="flex min-w-[120px] flex-col items-center">
            {isCompleted && hasActualScore ? (
              <>
                <span className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  Final score
                </span>

                <div className="mt-2 rounded-lg bg-foreground px-4 py-2 text-2xl font-bold text-background">
                  {prediction.actual_home_goals}
                  <span className="mx-2 opacity-60">-</span>
                  {prediction.actual_away_goals}
                </div>

                <div className="mt-3 text-center">
                  <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                    Predicted
                  </div>

                  <div className="mt-1 font-semibold">
                    {prediction.most_likely_home_goals}
                    <span className="mx-2 text-muted-foreground">
                      -
                    </span>
                    {prediction.most_likely_away_goals}
                  </div>
                </div>
              </>
            ) : (
              <>
                <span className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  VS
                </span>

                <div className="mt-2 rounded-lg bg-muted px-3 py-2 text-xl font-bold">
                  {prediction.most_likely_home_goals}
                  <span className="mx-2 text-muted-foreground">
                    -
                  </span>
                  {prediction.most_likely_away_goals}
                </div>

                <span className="mt-2 text-xs text-muted-foreground">
                  Predicted score
                </span>
              </>
            )}
          </div>

          <div className="flex min-w-0 flex-col items-center gap-3 text-center">
            <TeamLogo
              name={prediction.away_team.name}
              logoUrl={prediction.away_team.logo_url}
            />

            <div className="min-w-0">
              <div
                dir="auto"
                className="truncate font-semibold"
              >
                {awayTeamName}
              </div>

              <div className="mt-1 text-xs text-muted-foreground">
                Away
              </div>
            </div>
          </div>
        </div>

        {isCompleted && (
          <div className="mt-6 rounded-xl border bg-muted/20 p-4">
            <div className="flex flex-wrap items-center justify-center gap-2">
              <EvaluationBadge
                correct={prediction.outcome_correct}
                successText="Outcome correct"
                failureText="Outcome incorrect"
              />

              <EvaluationBadge
                correct={prediction.exact_score_correct}
                successText="Exact score"
                failureText="Exact score missed"
              />
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3 text-center sm:grid-cols-4">
              <div className="rounded-lg bg-background p-3">
                <div className="text-xs text-muted-foreground">
                  Predicted outcome
                </div>

                <div className="mt-1 text-sm font-bold">
                  {getOutcomeLabel(
                    prediction.predicted_outcome,
                  )}
                </div>
              </div>

              <div className="rounded-lg bg-background p-3">
                <div className="text-xs text-muted-foreground">
                  Actual outcome
                </div>

                <div className="mt-1 text-sm font-bold">
                  {getOutcomeLabel(
                    prediction.actual_outcome,
                  )}
                </div>
              </div>

              <div className="rounded-lg bg-background p-3">
                <div className="text-xs text-muted-foreground">
                  Brier score
                </div>

                <div className="mt-1 text-sm font-bold">
                  {prediction.brier_score !== null &&
                  prediction.brier_score !== undefined
                    ? prediction.brier_score.toFixed(3)
                    : "—"}
                </div>
              </div>

              <div className="rounded-lg bg-background p-3">
                <div className="text-xs text-muted-foreground">
                  Log loss
                </div>

                <div className="mt-1 text-sm font-bold">
                  {prediction.log_loss !== null &&
                  prediction.log_loss !== undefined
                    ? prediction.log_loss.toFixed(3)
                    : "—"}
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="mt-6 rounded-xl border bg-muted/20 p-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="text-xs uppercase tracking-wide text-muted-foreground">
                Predicted outcome
              </div>

              <div className="mt-1 text-lg font-bold">
                {predictedTeamName}
              </div>
            </div>

            <div className="sm:text-right">
              <div className="text-sm font-semibold">
                {getOutcomeLabel(
                  prediction.predicted_outcome,
                )}
              </div>

              <div className="mt-1 text-xs text-muted-foreground">
                Model confidence{" "}
                {(prediction.confidence * 100).toFixed(0)}%
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 space-y-4">
          <ProbabilityBar
            label={`${homeTeamName} Win`}
            value={prediction.home_win_probability}
          />

          <ProbabilityBar
            label="Draw"
            value={prediction.draw_probability}
          />

          <ProbabilityBar
            label={`${awayTeamName} Win`}
            value={prediction.away_win_probability}
          />
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3">
          <div className="rounded-xl bg-muted/40 p-4 text-center">
            <div className="text-xs uppercase tracking-wide text-muted-foreground">
              {homeTeamName} xG
            </div>

            <div className="mt-1 text-2xl font-bold">
              {prediction.home_expected_goals.toFixed(2)}
            </div>
          </div>

          <div className="rounded-xl bg-muted/40 p-4 text-center">
            <div className="text-xs uppercase tracking-wide text-muted-foreground">
              {awayTeamName} xG
            </div>

            <div className="mt-1 text-2xl font-bold">
              {prediction.away_expected_goals.toFixed(2)}
            </div>
          </div>
        </div>

        <div
          dir="ltr"
          className="mt-4 grid grid-cols-3 gap-3 border-t pt-4 text-center"
        >
          <div>
            <div className="text-xs text-muted-foreground">
              Home
            </div>

            <div className="mt-1 font-semibold">
              {(
                prediction.home_win_probability * 100
              ).toFixed(1)}
              %
            </div>
          </div>

          <div>
            <div className="text-xs text-muted-foreground">
              Draw
            </div>

            <div className="mt-1 font-semibold">
              {(
                prediction.draw_probability * 100
              ).toFixed(1)}
              %
            </div>
          </div>

          <div>
            <div className="text-xs text-muted-foreground">
              Away
            </div>

            <div className="mt-1 font-semibold">
              {(
                prediction.away_win_probability * 100
              ).toFixed(1)}
              %
            </div>
          </div>
        </div>
      </div>
    </article>
  );
}
