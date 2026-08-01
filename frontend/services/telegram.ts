import { api } from "@/lib/api";
export interface TelegramIdentity {chat_id:number;telegram_user_id:number|null;user_id:string;username:string;role:string;enabled:boolean;alerts:Record<string,boolean>}
export interface TelegramDestination {chat_id:number;title:string;chat_type:"private"|"group"|"supergroup"|"channel";enabled:boolean;activated_at:string;publish_prediction_new:boolean;publish_prediction_changed:boolean;publish_update_success:boolean;publish_update_failure:boolean}
export const getTelegramIdentities=()=>api<TelegramIdentity[]>("/api/v1/admin/telegram");
export const saveTelegramIdentity=(payload:{chat_id:number;telegram_user_id:number|null;user_id:string;enabled:boolean})=>api<TelegramIdentity>("/api/v1/admin/telegram",{method:"PUT",body:JSON.stringify(payload)});
export const getTelegramDestinations=()=>api<TelegramDestination[]>("/api/v1/admin/telegram/destinations");
export const saveTelegramDestination=(payload:Omit<TelegramDestination,"activated_at">)=>api<TelegramDestination>("/api/v1/admin/telegram/destinations",{method:"PUT",body:JSON.stringify(payload)});
