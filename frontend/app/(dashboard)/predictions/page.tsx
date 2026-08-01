"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  getPredictions,
  PredictionView,
} from "@/services/predictions";
import { PredictionCard } from "@/components/predictions/prediction-card";
import { Prediction } from "@/types/prediction";

type TabDefinition = {
  value: PredictionTabView;
  label: string;
  description: string;
};

type PredictionTabView = Exclude<PredictionView, "all">;

const tabs: TabDefinition[] = [
  {
    value: "upcoming",
    label: "Upcoming",
    description:
      "Upcoming matches ordered by the nearest kickoff time.",
  },
  {
    value: "completed",
    label: "Completed",
    description:
      "Completed matches with predicted and actual results.",
  },
];

export function sortUpcomingPredictions(items: Prediction[]): Prediction[] {
  return [...items].sort((left,right)=>{
    const leftTime=Date.parse(left.kickoff_at); const rightTime=Date.parse(right.kickoff_at);
    if (Number.isNaN(leftTime)) return Number.isNaN(rightTime)?left.fixture_id.localeCompare(right.fixture_id):1;
    if (Number.isNaN(rightTime)) return -1;
    return leftTime-rightTime || left.fixture_id.localeCompare(right.fixture_id);
  });
}

export default function PredictionsPage() {
  const [activeView, setActiveView] =
    useState<PredictionTabView>("upcoming");

  const {
    data: predictions = [],
    isLoading,
    isFetching,
    error,
    refetch,
  } = useQuery({
    queryKey: ["predictions", activeView],
    queryFn: () => getPredictions(activeView),
  });

  const activeTab =
    tabs.find((tab) => tab.value === activeView) ??
    tabs[0];
  const visiblePredictions = activeView === "upcoming" ? sortUpcomingPredictions(predictions) : predictions;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Predictions
          </h1>

          <p className="mt-2 text-muted-foreground">
            AI match predictions, probabilities and result
            evaluation.
          </p>
        </div>

        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="inline-flex h-10 items-center justify-center rounded-lg border bg-background px-4 text-sm font-medium transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isFetching ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <div className="rounded-2xl border bg-card p-2 shadow-sm">
        <div
          className="grid grid-cols-2 gap-2"
          role="tablist"
          aria-label="Prediction views"
        >
          {tabs.map((tab) => {
            const isActive =
              activeView === tab.value;

            return (
              <button
                key={tab.value}
                type="button"
                role="tab"
                aria-selected={isActive}
                onClick={() =>
                  setActiveView(tab.value)
                }
                className={[
                  "rounded-xl px-4 py-3 text-sm font-semibold transition-all",
                  isActive
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                ].join(" ")}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>
            <section className="space-y-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold">
              {activeTab.label} predictions
            </h2>

            <p className="mt-1 text-sm text-muted-foreground">
              {activeTab.description}
            </p>
          </div>

          {!isLoading && !error && (
            <div className="text-sm text-muted-foreground">
              {visiblePredictions.length}{" "}
              {visiblePredictions.length === 1
                ? "prediction"
                : "predictions"}
            </div>
          )}
        </div>

        {isLoading ? (
          <div className="grid gap-6">
            {Array.from({ length: 3 }).map(
              (_, index) => (
                <div
                  key={index}
                  className="h-80 animate-pulse rounded-2xl border bg-muted/40"
                />
              ),
            )}
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-destructive/40 bg-destructive/10 p-6">
            <h3 className="font-semibold text-destructive">
              Failed to load predictions
            </h3>

            <p className="mt-2 text-sm text-muted-foreground">
              The predictions could not be loaded from the
              server.
            </p>

            <button
              type="button"
              onClick={() => refetch()}
              className="mt-4 inline-flex h-10 items-center justify-center rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              Try again
            </button>
          </div>
        ) : visiblePredictions.length === 0 ? (
          <div className="rounded-2xl border border-dashed p-10 text-center">
            <h3 className="font-semibold">
              No {activeView} predictions
            </h3>

            <p className="mt-2 text-sm text-muted-foreground">
              {activeView === "upcoming"
                ? "There are currently no upcoming predictions."
                : "There are currently no completed predictions."}
            </p>
          </div>
        ) : (
          <div className="grid gap-6">
            {visiblePredictions.map((prediction) => (
              <PredictionCard
                key={prediction.id}
                prediction={prediction}
                view={activeView}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
