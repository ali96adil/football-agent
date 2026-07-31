"use client";

import { Bell, Moon, Search } from "lucide-react";

export default function AppHeader() {
  return (
    <header className="flex h-16 items-center justify-between border-b bg-background px-6">
      <h2 className="text-xl font-semibold">لوحة التحكم</h2>

      <div className="flex items-center gap-3">
        <button
          type="button"
          aria-label="البحث"
          className="rounded-lg border p-2 hover:bg-accent"
        >
          <Search className="h-5 w-5" />
        </button>

        <button
          type="button"
          aria-label="الإشعارات"
          className="rounded-lg border p-2 hover:bg-accent"
        >
          <Bell className="h-5 w-5" />
        </button>

        <button
          type="button"
          aria-label="تغيير المظهر"
          className="rounded-lg border p-2 hover:bg-accent"
        >
          <Moon className="h-5 w-5" />
        </button>

        <div className="mr-3 rounded-full border px-3 py-2 text-sm font-medium">
          علي
        </div>
      </div>
    </header>
  );
}
