"use client";

import { CalendarDays, Trophy, Radio, ListOrdered } from "lucide-react";

interface Props {
  total: number;
  today: number;
  live: number;
  competitions: number;
}

function StatCard({
  icon,
  title,
  value,
}: {
  icon: React.ReactNode;
  title: string;
  value: number;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-sm transition hover:border-blue-500 hover:shadow-lg">
      <div className="flex items-center justify-between">
        {icon}

        <span className="text-3xl font-black text-white">
          {value}
        </span>
      </div>

      <p className="mt-4 text-sm text-slate-400">
        {title}
      </p>
    </div>
  );
}

export function FixtureStats({
  total,
  today,
  live,
  competitions,
}: Props) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard
        icon={<ListOrdered className="h-6 w-6 text-blue-400" />}
        title="إجمالي المباريات"
        value={total}
      />

      <StatCard
        icon={<CalendarDays className="h-6 w-6 text-emerald-400" />}
        title="مباريات اليوم"
        value={today}
      />

      <StatCard
        icon={<Radio className="h-6 w-6 text-red-400" />}
        title="مباشرة الآن"
        value={live}
      />

      <StatCard
        icon={<Trophy className="h-6 w-6 text-yellow-400" />}
        title="البطولات"
        value={competitions}
      />
    </div>
  );
}