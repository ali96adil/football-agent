"use client";

import AppHeader from "./app-header";
import AppSidebar from "./app-sidebar";

export default function AppShell({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      <AppSidebar />

      <div className="flex flex-1 flex-col">
        <AppHeader />

        <main className="flex-1 bg-slate-50 p-4 dark:bg-slate-900 sm:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
