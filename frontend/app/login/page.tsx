"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";

export default function LoginPage() {
  const [username, setUsername] = useState(""); const [password, setPassword] = useState("");
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const router = useRouter(); const queryClient = useQueryClient();
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const result = await api<{ user: unknown }>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
      queryClient.setQueryData(["auth", "me"], result.user); router.replace("/");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "تعذر تسجيل الدخول"); }
    finally { setBusy(false); }
  }
  return <main className="grid min-h-screen place-items-center bg-[radial-gradient(circle_at_top,#164e63,#020617_55%)] p-6">
    <form onSubmit={submit} className="w-full max-w-md rounded-3xl border border-cyan-500/20 bg-slate-950/90 p-8 text-slate-100 shadow-2xl backdrop-blur">
      <div className="mb-8 flex items-center gap-3"><span className="rounded-2xl bg-cyan-500/15 p-3 text-cyan-300"><ShieldCheck /></span><div><h1 className="text-2xl font-bold">Football Agent</h1><p className="text-sm text-slate-400">بوابة تشغيل منصة كرة القدم</p></div></div>
      <label className="mb-2 block text-sm">اسم المستخدم</label><input dir="ltr" autoComplete="username" value={username} onChange={e=>setUsername(e.target.value)} className="mb-5 w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 outline-none focus:border-cyan-400" required />
      <label className="mb-2 block text-sm">كلمة المرور</label><input dir="ltr" type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} className="mb-5 w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 outline-none focus:border-cyan-400" required />
      {error && <p role="alert" className="mb-4 rounded-xl bg-red-950 p-3 text-sm text-red-200">{error}</p>}
      <button disabled={busy} className="w-full rounded-xl bg-cyan-500 py-3 font-bold text-slate-950 disabled:opacity-50">{busy ? "جارٍ الدخول…" : "تسجيل الدخول"}</button>
      <p className="mt-6 text-center text-xs text-slate-500">جلسة آمنة بصلاحيات محددة — 1.0.0-dev.5</p>
    </form>
  </main>;
}
