"use client";

import { useState } from "react";
import AppHeader from "./app-header";
import AppSidebar from "./app-sidebar";

export default function AppShell({
  children,
}: {
  children: React.ReactNode;
}) {
  const [navigationOpen, setNavigationOpen] = useState(false);
  return (
    <div className="flex min-h-screen min-w-0 overflow-x-hidden">
      <AppSidebar open={navigationOpen} onClose={() => setNavigationOpen(false)} />

      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader onMenu={() => setNavigationOpen(true)} menuOpen={navigationOpen} />

        <main className="flex-1 bg-slate-50 p-4 dark:bg-slate-900 sm:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
