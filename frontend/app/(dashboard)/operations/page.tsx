"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Play, RefreshCcw, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { canOperate, useAuth } from "@/hooks/use-auth";
import { getOperations, JobRecord, retryJob, runAction } from "@/services/operations";

const actions = [["sync","مزامنة البيانات"],["snapshots","بناء Snapshots"],["predictions","تشغيل التوقعات"],["evaluation","تقييم المكتمل"]];
const statuses: Record<JobRecord["status"], string> = { queued:"بانتظار التنفيذ", running:"قيد التشغيل", retry:"بانتظار إعادة المحاولة", succeeded:"نجحت", failed:"فشلت", dead_letter:"متوقفة نهائيًا" };
const safeReasons: Record<string,string> = { timeout:"انتهت مهلة التنفيذ", http_status:"رفض مصدر البيانات الطلب", rate_limit:"تم بلوغ حد طلبات المصدر", source_disabled:"المصدر معطّل", authentication_failure:"فشل توثيق مصدر البيانات", invalid_response:"استجابة المصدر غير صالحة", database_failure:"تعذّر حفظ البيانات", dependency_failure:"فشلت خدمة تابعة", connection_failure:"تعذّر الاتصال بالمصدر", "worker lease expired":"انقطع العامل قبل إنهاء المهمة" };
const stamp=(value:string|null)=>value?new Date(value).toLocaleString("ar-IQ",{timeZone:"Asia/Baghdad"}):"—";
const reason=(job:JobRecord)=>{const code=String(job.result?.reason??job.last_error??"");return code?(safeReasons[code]??"تعذّر إكمال المهمة؛ راجع السجل التشغيلي"):"—"};

export default function OperationsPage() {
  const { user }=useAuth(); const client=useQueryClient();
  const query=useQuery({queryKey:["operations"],queryFn:getOperations,refetchInterval:5000});
  const action=useMutation({mutationFn:runAction,onSuccess:()=>{toast.success("تمت إضافة المهمة إلى قائمة الانتظار");client.invalidateQueries({queryKey:["operations"]})},onError:e=>toast.error(e.message)});
  const retry=useMutation({mutationFn:retryJob,onSuccess:()=>client.invalidateQueries({queryKey:["operations"]}),onError:e=>toast.error(e.message)});
  return <div className="space-y-6"><header><p className="text-sm text-cyan-700">تشغيل غير متزامن وآمن</p><h1 className="text-3xl font-black">المهام والتحكم</h1><p className="text-muted-foreground">تظهر النتائج والتقدم من PostgreSQL دون تجميد الواجهة.</p></header>
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{actions.map(([key,label])=><button key={key} disabled={!canOperate(user?.role)||action.isPending} onClick={()=>window.confirm(`تأكيد: ${label}؟`)&&action.mutate(key)} className="flex items-center justify-between rounded-2xl border bg-white p-5 text-right shadow-sm hover:border-cyan-400 disabled:opacity-40 dark:bg-slate-950"><span><b>{label}</b><small className="mt-1 block text-muted-foreground">سيعمل عبر worker</small></span><Play className="text-cyan-600"/></button>)}</section>
    <section className="overflow-hidden rounded-2xl border bg-white dark:bg-slate-950">
      <div className="flex items-center justify-between border-b p-4">
        <h2 className="font-bold">قائمة المهام</h2>
        <button aria-label="تحديث المهام" onClick={()=>query.refetch()}><RefreshCcw size={18}/></button>
      </div>
      <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-sm">
        <thead className="bg-slate-100 dark:bg-slate-900"><tr>{["المهمة والمصدر","الحالة والمرحلة","المحاولة","التوقيت","التفاصيل"].map(x=><th className="p-3 text-right" key={x}>{x}</th>)}</tr></thead>
        <tbody>{query.data?.jobs.map(job=><tr className="border-t align-top" key={job.id}>
          <td className="p-3"><b dir="ltr">{job.job_type}</b><small className="block text-muted-foreground">{job.requested_via} {job.requested_by&&`· ${job.requested_by}`}</small></td>
          <td className="p-3"><b>{statuses[job.status]}</b><small className="block text-muted-foreground">{String(job.result?.stage ?? job.result?.failed_stage ?? "—")}</small></td>
          <td className="p-3">{job.status==="succeeded"?`نجحت في المحاولة ${job.attempt_count}`:`المحاولة ${job.attempt_count} من ${job.max_attempts}`}</td>
          <td className="p-3"><dl><dt>البدء</dt><dd>{stamp(job.started_at)}</dd><dt>الانتهاء</dt><dd>{stamp(job.finished_at)}</dd>{job.status==="running"&&<><dt>آخر نبضة</dt><dd>{stamp(job.heartbeat_at)}</dd></>}</dl></td>
          <td className="max-w-sm p-3"><details><summary className="cursor-pointer">عرض السبب والنتيجة</summary><p className="mt-2 text-red-700">{reason(job)}</p>{Boolean(job.result?.status)&&<p className="mt-2 text-xs text-muted-foreground">نتيجة المعالجة: {String(job.result?.status)}</p>}</details>{["failed","dead_letter"].includes(job.status)&&canOperate(user?.role)&&<button onClick={()=>window.confirm("إعادة محاولة هذه المهمة؟")&&retry.mutate(job.id)} className="mt-2 flex items-center gap-1 text-cyan-700"><RotateCcw size={14}/>إعادة المحاولة</button>}</td>
        </tr>)}</tbody>
      </table></div>
    </section>
  </div>;
}
