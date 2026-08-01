"use client";

import { Bell, LogOut } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";

export default function AppHeader() {
  const { user, logout } = useAuth();
  return (
    <header className="flex h-16 items-center justify-between border-b bg-background px-6">
      <div><h2 className="text-lg font-semibold">مركز عمليات Football Agent</h2><p className="text-xs text-muted-foreground">بيانات حقيقية وحالة تشغيل مباشرة</p></div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          aria-label="الإشعارات"
          className="rounded-lg border p-2 hover:bg-accent"
        >
          <Bell className="h-5 w-5" />
        </button>

        <button
          type="button"
          aria-label="تسجيل الخروج"
          onClick={() => logout()}
          className="rounded-lg border p-2 hover:bg-accent"
        >
          <LogOut className="h-5 w-5" />
        </button>

        <div className="mr-3 rounded-full border px-3 py-2 text-sm font-medium">
          {user?.display_name} · {user?.role}
        </div>
      </div>
    </header>
  );
}
