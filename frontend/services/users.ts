import { api } from "@/lib/api";
import type { Role } from "@/hooks/use-auth";
export interface UserRecord { id:string;username:string;display_name:string;role:Role;is_active:boolean;created_at:string;last_login_at:string|null }
export const getUsers=()=>api<UserRecord[]>("/api/v1/admin/users");
export const createUser=(payload:{username:string;display_name:string;password:string;role:Role})=>api<UserRecord>("/api/v1/admin/users",{method:"POST",body:JSON.stringify(payload)});
export const updateUser=(id:string,payload:Partial<Pick<UserRecord,"display_name"|"role"|"is_active">>)=>api<UserRecord>(`/api/v1/admin/users/${id}`,{method:"PATCH",body:JSON.stringify(payload)});
