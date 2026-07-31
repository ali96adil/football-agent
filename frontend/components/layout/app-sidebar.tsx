"use client";

import Link from "next/link";
import {
  LayoutDashboard,
  CalendarDays,
  Users,
  Brain,
  BarChart3,
  Settings,
  Trophy,
} from "lucide-react";

const navigation = [
  {
    title: "لوحة التحكم",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    title: "المباريات",
    href: "/matches",
    icon: CalendarDays,
  },
  {
    title: "الفرق",
    href: "/teams",
    icon: Users,
  },
  {
    title: "التوقعات",
    href: "/predictions",
    icon: Brain,
  },
  {
    title: "التحليلات",
    href: "/analytics",
    icon: BarChart3,
  },
  {
    title: "النماذج",
    href: "/models",
    icon: Trophy,
  },
  {
    title: "الإعدادات",
    href: "/settings",
    icon: Settings,
  },
];

export default function AppSidebar() {
  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-l bg-background">
      <div className="border-b px-6 py-5">
        <h1 className="text-xl font-bold">
          ⚽ ذكاء كرة القدم
        </h1>

        <p className="mt-1 text-sm text-muted-foreground">
          منصة التحليل والتوقعات
        </p>
      </div>

      <nav className="flex-1 space-y-1 p-4">
        {navigation.map((item) => {
          const Icon = item.icon;

          return (
            <Link
              key={item.title}
              href={item.href}
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              <Icon className="h-5 w-5" />
              <span>{item.title}</span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-4 text-xs text-muted-foreground">
        الإصدار 0.1.0
      </div>
    </aside>
  );
}
