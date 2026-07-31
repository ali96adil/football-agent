import { api } from "@/lib/api";

export interface DashboardResponse {
  system: {
    status: string;
    version: string;
  };

  stats: {
    fixtures: number;
    teams: number;
    competitions: number;
    predictions: number;
    scheduled: number;
    live: number;
    finished: number;
  };
}

export function getDashboard() {
  return api<DashboardResponse>(
    "/api/v1/dashboard"
  );
}
