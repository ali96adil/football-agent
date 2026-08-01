"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Play, RefreshCcw, RotateCcw } from "lucide-react";
import { canOperate, useAuth } from "@/hooks/use-auth";
import { getOperations, retryJob, runAction } from "@/services/operations";

const actions = [["sync","مزامنة البيانات"],["snapshots","بناء Snapshots"],["predictions","تشغيل التوقعات"],["evaluation","تقييم المكتمل"]];
export default function OperationsPage() {
  const { user }=useAuth(); const client=useQueryClient();
  const query=useQuery({queryKey:["operations"],queryFn:getOperations,refetchInterval:5000});
  const action=useMutation({mutationFn:runAction,onSuccess:()=>{toast.success("تمت إضافة المهمة إلى قائمة الانتظار");client.invalidateQueries({queryKey:["operations"]})},onError:e=>toast.error(e.message)});
  const retry=useMutation({mutationFn:retryJob,onSuccess:()=>client.invalidateQueries({queryKey:["operations"]}),onError:e=>toast.error(e.message)});
  return <div className="space-y-6"><header><p className="text-sm text-cyan-700">تشغيل غير متزامن وآمن</p><h1 className="text-3xl font-black">المهام والتحكم</h1><p className="text-muted-foreground">تظهر النتائج والتقدم من PostgreSQL دون تجميد الواجهة.</p></header>
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{actions.map(([key,label])=><button key={key} disabled={!canOperate(user?.role)||action.isPending} onClick={()=>window.confirm(`تأكيد: ${label}؟`)&&action.mutate(key)} className="flex items-center justify-between rounded-2xl border bg-white p-5 text-right shadow-sm hover:border-cyan-400 disabled:opacity-40 dark:bg-slate-950"><span><b>{label}</b><small className="mt-1 block text-muted-foreground">سيعمل عبر worker</small></span><Play className="text-cyan-600"/></button>)}</section>
    <section className="overflow-hidden rounded-2xl border bg-white dark:bg-slate-950"><div className="flex items-center justify-between border-b p-4"><h2 className="font-bold">قائمة المهام</h2><button onClick={()=>query.refetch()}><RefreshCcw size={18}/></button></div><div className="overflow-x-auto"><table className="w-full text-sm"><thead className="bg-slate-100 dark:bg-slate-900"><tr>{["المهمة","الحالة","المحاولات","الوقت","النتيجة"].map(x=><th className="p-3 text-right" key={x}>{x}</th>)}</tr></thead><tbody>{query.data?.jobs.map(job=><tr className="border-t" key={job.id}><td className="p-3"><b dir="ltr">{job.job_type}</b><small className="block text-muted-foreground">{job.requested_via}</small></td><td className="p-3">{job.status}</td><td className="p-3">{job.attempt_count}/{job.max_attempts}</td><td className="p-3">{new Date(job.created_at).toLocaleString("ar-IQ")}</td><td className="max-w-xs p-3"><span className="line-clamp-2 text-red-700">{job.last_error}</span>{["failed","dead_letter"].includes(job.status)&&canOperate(user?.role)&&<button onClick={()=>window.confirm("إعادة محاولة هذه المهمة؟")&&retry.mutate(job.id)} className="mt-1 flex items-center gap-1 text-cyan-700"><RotateCcw size={14}/>إعادة المحاولة</button>}</td></tr>)}</tbody></table></div></section>
  </div>;
}
