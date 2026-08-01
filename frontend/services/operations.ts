import { api } from "@/lib/api";

export interface JobRecord { id:string; job_type:string; status:string; attempt_count:number; max_attempts:number; created_at:string; started_at:string|null; finished_at:string|null; last_error:string|null; result:Record<string,unknown>|null; requested_via:string; requested_by:string|null }
export interface SourceRecord { id:string; code:string; name:string; enabled:boolean; priority:number; reliability_score:number; requests_used_today:number; last_success_at:string|null; last_failure_at:string|null }
export interface AuditRecord { id:number; occurred_at:string; actor_username:string|null; actor_role:string|null; action:string; target_type:string|null; target_id:string|null; outcome:string; details:Record<string,unknown> }
export interface OperationsResponse { jobs:JobRecord[]; sources:SourceRecord[]; audit:AuditRecord[]; settings:Record<string,unknown> }

export const getOperations = () => api<OperationsResponse>("/api/v1/operations");
export const runAction = (action:string) => api<{id:string;status:string}>(`/api/v1/operations/actions/${action}`, { method:"POST", body:JSON.stringify({}) });
export const retryJob = (id:string) => api(`/api/v1/operations/jobs/${id}/retry`, { method:"POST" });
export const updateSource = (id:string, enabled:boolean) => api(`/api/v1/operations/sources/${id}?enabled=${enabled}`, { method:"PATCH" });
export const updateSettings = (values:Record<string,unknown>) => api("/api/v1/operations/settings", { method:"PATCH", body:JSON.stringify(values) });
