"use client";

import { Bell, LogOut, Menu } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";

export default function AppHeader({ onMenu, menuOpen }: { onMenu: () => void; menuOpen: boolean }) {
  const { user, logout } = useAuth();
  return (
    <header className="flex min-h-16 items-center justify-between gap-2 border-b bg-background px-3 sm:px-6">
      <div className="flex min-w-0 items-center gap-2">
        <button type="button" onClick={onMenu} aria-label="فتح قائمة التنقل" aria-expanded={menuOpen} aria-controls="mobile-navigation" className="shrink-0 rounded-lg border p-2 hover:bg-accent lg:hidden"><Menu className="h-5 w-5" /></button>
        <div className="min-w-0"><h2 className="truncate text-sm font-semibold sm:text-lg">مركز عمليات Football Agent</h2><p className="hidden text-xs text-muted-foreground sm:block">بيانات حقيقية وحالة تشغيل مباشرة</p></div>
      </div>

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

        <div className="hidden rounded-full border px-3 py-2 text-sm font-medium sm:block">
          {user?.display_name} · {user?.role}
        </div>
      </div>
    </header>
  );
}
