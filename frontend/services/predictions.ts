import { api } from "@/lib/api";
import { Prediction } from "@/types/prediction";

export type PredictionView =
  | "upcoming"
  | "completed"
  | "all";

export function getPredictions(
  view: PredictionView = "upcoming",
): Promise<Prediction[]> {
  return api<Prediction[]>(
    `/api/v1/predictions?view=${view}`,
  );
}

export function getPrediction(
  fixtureId: string,
): Promise<Prediction> {
  return api<Prediction>(
    `/api/v1/predictions/${fixtureId}`,
  );
}