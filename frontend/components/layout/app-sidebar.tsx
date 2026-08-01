"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import {
  LayoutDashboard,
  CalendarDays,
  Brain,
  Database,
  ListChecks,
  Shield,
  ScrollText,
  Settings,
  X,
} from "lucide-react";
import { useAuth } from "@/hooks/use-auth";

const navigation = [
  {
    title: "لوحة التحكم",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    title: "المباريات",
    href: "/fixtures",
    icon: CalendarDays,
  },
  {
    title: "مصادر البيانات",
    href: "/sources",
    icon: Database,
  },
  {
    title: "التوقعات",
    href: "/predictions",
    icon: Brain,
  },
  {
    title: "المهام والتحكم",
    href: "/operations",
    icon: ListChecks,
  },
  {
    title: "المستخدمون والصلاحيات",
    href: "/admin/users",
    icon: Shield,
    admin: true,
  },
  {
    title: "سجل الإجراءات",
    href: "/audit",
    icon: ScrollText,
  },
  {
    title: "الإعدادات",
    href: "/settings",
    icon: Settings,
  },
];

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();
  return (
    <>
      <div className="border-b px-6 py-5">
        <h1 className="text-xl font-bold">
          ⚽ ذكاء كرة القدم
        </h1>

        <p className="mt-1 text-sm text-muted-foreground">
          منصة التحليل والتوقعات
        </p>
      </div>

      <nav className="flex-1 space-y-1 p-4">
        {navigation.filter(item => !item.admin || user?.role === "admin").map((item) => {
          const Icon = item.icon;

          return (
            <Link
              key={item.title}
              href={item.href}
              onClick={onNavigate}
              className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-300 transition-colors hover:bg-cyan-500/10 hover:text-cyan-200"
            >
              <Icon className="h-5 w-5" />
              <span>{item.title}</span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-4 text-xs text-muted-foreground">
        <span dir="ltr">1.0.0-dev.5</span>
      </div>
    </>
  );
}

export default function AppSidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const closeButton = useRef<HTMLButtonElement>(null);
  const drawer = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButton.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab") return;
      const focusable = Array.from(drawer.current?.querySelectorAll<HTMLElement>('a[href],button:not([disabled])') ?? []);
      if (!focusable.length) return;
      const first = focusable[0]; const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => { document.body.style.overflow = previousOverflow; document.removeEventListener("keydown", onKeyDown); previouslyFocused?.focus(); };
  }, [open, onClose]);

  return <>
    <aside className="hidden h-screen w-72 shrink-0 flex-col border-l bg-slate-950 text-slate-100 lg:flex"><SidebarContent /></aside>
    {open && <div className="fixed inset-0 z-50 lg:hidden">
      <button type="button" className="absolute inset-0 bg-black/55" aria-label="إغلاق قائمة التنقل" onClick={onClose} />
      <aside ref={drawer} id="mobile-navigation" role="dialog" aria-modal="true" aria-label="قائمة التنقل" className="absolute inset-y-0 right-0 flex w-[min(18rem,88vw)] flex-col border-l bg-slate-950 text-slate-100 shadow-2xl">
        <button ref={closeButton} type="button" onClick={onClose} aria-label="إغلاق قائمة التنقل" className="absolute left-3 top-3 rounded-lg border border-slate-700 p-2"><X className="h-5 w-5" /></button>
        <SidebarContent onNavigate={onClose} />
      </aside>
    </div>}
  </>;
}
