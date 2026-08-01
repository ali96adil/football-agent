import { api } from "@/lib/api";

export interface DashboardResponse {
  system: {
    status: string;
    version: string;
  };

  operations: {
    data_mode: "real" | "unverified";
    last_data_update_at: string | null;
    sources: Array<{
      code: string;
      name: string;
      enabled: boolean;
      configured: boolean;
      scheduled: boolean;
      last_success_at: string | null;
      last_failure_at: string | null;
      requests_used_today: number;
    }>;
    worker: {
      worker_id: string;
      status: "idle" | "running" | "stopping";
      heartbeat_at: string;
      scheduler_enabled: boolean;
      schedule_interval_seconds: number;
      next_sync_at: string | null;
    } | null;
    jobs: {
      pending: number;
      running: number;
      dead_letter: number;
      last_sync_at: string | null;
      last_sync_failure_at: string | null;
    };
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
