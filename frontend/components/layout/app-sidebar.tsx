"use client";

import Link from "next/link";
import {
  LayoutDashboard,
  CalendarDays,
  Brain,
  Database,
  ListChecks,
  Shield,
  ScrollText,
  Settings,
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

export default function AppSidebar() {
  const { user } = useAuth();
  return (
    <aside className="hidden h-screen w-72 shrink-0 flex-col border-l bg-slate-950 text-slate-100 lg:flex">
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
    </aside>
  );
}
