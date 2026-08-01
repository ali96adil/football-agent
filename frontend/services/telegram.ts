import { api } from "@/lib/api";
export interface TelegramIdentity {chat_id:number;telegram_user_id:number|null;user_id:string;username:string;role:string;enabled:boolean;alerts:Record<string,boolean>}
export const getTelegramIdentities=()=>api<TelegramIdentity[]>("/api/v1/admin/telegram");
export const saveTelegramIdentity=(payload:{chat_id:number;telegram_user_id:number|null;user_id:string;enabled:boolean})=>api<TelegramIdentity>("/api/v1/admin/telegram",{method:"PUT",body:JSON.stringify(payload)});
