"use client";

import {
  Activity,
  Brain,
  CalendarDays,
  CheckCircle2,
  Database,
  RefreshCw,
  Server,
  ShieldCheck,
  Target,
  Trophy,
  Users,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { useDashboard } from "@/hooks/use-dashboard";

const numberFormatter = new Intl.NumberFormat("ar-IQ");

function DashboardSkeleton() {
  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <div className="h-4 w-40 animate-pulse rounded bg-muted" />
        <div className="h-9 w-56 animate-pulse rounded bg-muted" />
        <div className="h-4 w-full max-w-2xl animate-pulse rounded bg-muted" />
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Card key={index}>
            <CardHeader className="space-y-3">
              <div className="h-4 w-28 animate-pulse rounded bg-muted" />
            </CardHeader>

            <CardContent className="space-y-3">
              <div className="h-9 w-20 animate-pulse rounded bg-muted" />
              <div className="h-3 w-40 animate-pulse rounded bg-muted" />
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <Card key={index}>
            <CardHeader>
              <div className="h-5 w-32 animate-pulse rounded bg-muted" />
            </CardHeader>

            <CardContent>
              <div className="h-24 animate-pulse rounded-lg bg-muted" />
            </CardContent>
          </Card>
        ))}
      </section>
    </div>
  );
}

export default function DashboardPage() {
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
    dataUpdatedAt,
  } = useDashboard();

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (isError || !data) {
    return (
      <div className="flex min-h-[420px] items-center justify-center">
        <Card className="w-full max-w-lg">
          <CardHeader>
            <CardTitle>تعذر تحميل لوحة التحكم</CardTitle>

            <CardDescription>
              لم يتمكن النظام من الاتصال بخدمة جمع البيانات.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <div
              className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"
              dir="ltr"
            >
              {error instanceof Error
                ? error.message
                : "Unknown dashboard error"}
            </div>

            <button
              type="button"
              onClick={() => refetch()}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={isFetching}
            >
              <RefreshCw
                className={`h-4 w-4 ${
                  isFetching ? "animate-spin" : ""
                }`}
              />

              إعادة المحاولة
            </button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const stats = [
    {
      title: "إجمالي المباريات",
      value: data.stats.fixtures,
      description: "جميع المباريات المخزنة في قاعدة البيانات",
      icon: Trophy,
    },
    {
      title: "الفرق",
      value: data.stats.teams,
      description: "عدد الفرق المسجلة في المنصة",
      icon: Users,
    },
    {
      title: "البطولات",
      value: data.stats.competitions,
      description: "البطولات التي يتابعها النظام",
      icon: Target,
    },
    {
      title: "التوقعات",
      value: data.stats.predictions,
      description: "التوقعات التي أنشأها محرك التحليل",
      icon: Brain,
    },
  ];

  const fixtureStats = [
    {
      title: "مباريات مجدولة",
      value: data.stats.scheduled,
      description: "مباريات لم تبدأ بعد",
      icon: CalendarDays,
    },
    {
      title: "مباريات مباشرة",
      value: data.stats.live,
      description: "مباريات جارية حاليًا",
      icon: Activity,
    },
    {
      title: "مباريات منتهية",
      value: data.stats.finished,
      description: "مباريات اكتملت وتم تخزين نتائجها",
      icon: CheckCircle2,
    },
  ];

  const updatedAt = dataUpdatedAt
    ? new Intl.DateTimeFormat("ar-IQ", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }).format(new Date(dataUpdatedAt))
    : "—";
  const formatTimestamp = (value: string | null) =>
    value
      ? new Intl.DateTimeFormat("ar-IQ", {
          dateStyle: "medium",
          timeStyle: "medium",
        }).format(new Date(value))
      : "لا يوجد تحديث مسجل";
  const workerFresh = data.operations.worker
    ? Date.now() - new Date(data.operations.worker.heartbeat_at).getTime() < 120000
    : false;

  return (
    <div className="space-y-8">
      <section className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex flex-col gap-2">
          <p className="text-sm text-muted-foreground">
            منصة ذكاء كرة القدم
          </p>

          <h1 className="text-3xl font-bold tracking-tight">
            نظرة عامة
          </h1>

          <p className="max-w-2xl text-sm text-muted-foreground">
            بيانات من خط الجمع وقاعدة PostgreSQL، مع تمييز صريح لحالة
            المصدر وآخر تحديث فعلي.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="text-xs text-muted-foreground">
            آخر تحديث: {updatedAt}
          </div>

          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="inline-flex h-9 items-center justify-center gap-2 rounded-md border bg-background px-3 text-sm font-medium transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw
              className={`h-4 w-4 ${
                isFetching ? "animate-spin" : ""
              }`}
            />

            تحديث
          </button>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>هوية الإصدار والبيانات</CardTitle>
            <CardDescription>هذه مرحلة تطويرية وليست v1.0.0 مكتملة</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p dir="ltr">v{data.system.version}</p>
            <p>
              نوع البيانات: {data.operations.data_mode === "real" ? "حقيقية من مزود خارجي" : "غير متحقق منها بعد"}
            </p>
            <p className="text-muted-foreground">
              آخر جمع فعلي: {formatTimestamp(data.operations.last_data_update_at)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Worker والجدولة</CardTitle>
            <CardDescription>حالة التنفيذ المستقاة من heartbeat في PostgreSQL</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>{workerFresh ? `يعمل: ${data.operations.worker?.status}` : "لا توجد heartbeat حديثة"}</p>
            <p>قيد الانتظار: {numberFormatter.format(data.operations.jobs.pending)}</p>
            <p>قيد التنفيذ: {numberFormatter.format(data.operations.jobs.running)}</p>
            <p>فشل نهائي: {numberFormatter.format(data.operations.jobs.dead_letter)}</p>
            <p className="text-muted-foreground">
              المزامنة التالية: {formatTimestamp(data.operations.worker?.next_sync_at ?? null)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>مصادر البيانات</CardTitle>
            <CardDescription>الإعداد وآخر نجاح لكل مصدر</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {data.operations.sources.map((source) => (
              <div key={source.code} className="rounded-md border p-2">
                <div className="flex items-center justify-between gap-2">
                  <span>{source.name}</span>
                  <span className={source.enabled && source.configured ? "text-emerald-600" : "text-amber-600"}>
                    {!source.enabled || !source.configured
                      ? "غير مهيأ"
                      : source.scheduled
                        ? "ضمن الجدولة"
                        : "مهيأ يدويًا"}
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  آخر نجاح: {formatTimestamp(source.last_success_at)}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {stats.map((item) => {
          const Icon = item.icon;

          return (
            <Card key={item.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {item.title}
                </CardTitle>

                <Icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>

              <CardContent>
                <div className="text-3xl font-bold tabular-nums">
                  {numberFormatter.format(item.value)}
                </div>

                <p className="mt-1 text-xs text-muted-foreground">
                  {item.description}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </section>

      <section>
        <div className="mb-4">
          <h2 className="text-xl font-semibold">حالة المباريات</h2>

          <p className="mt-1 text-sm text-muted-foreground">
            توزيع المباريات بحسب حالتها الحالية
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {fixtureStats.map((item) => {
            const Icon = item.icon;

            return (
              <Card key={item.title}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    {item.title}
                  </CardTitle>

                  <Icon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>

                <CardContent>
                  <div className="text-3xl font-bold tabular-nums">
                    {numberFormatter.format(item.value)}
                  </div>

                  <p className="mt-1 text-xs text-muted-foreground">
                    {item.description}
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>ملخص قاعدة البيانات</CardTitle>

            <CardDescription>
              الحجم الحالي للبيانات التي جمعها النظام
            </CardDescription>
          </CardHeader>

          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-lg border p-4">
                <div className="flex items-center gap-3">
                  <div className="rounded-md border p-2">
                    <Database className="h-5 w-5" />
                  </div>

                  <div>
                    <p className="text-sm text-muted-foreground">
                      إجمالي الكيانات الأساسية
                    </p>

                    <p className="text-2xl font-bold tabular-nums">
                      {numberFormatter.format(
                        data.stats.fixtures +
                          data.stats.teams +
                          data.stats.competitions
                      )}
                    </p>
                  </div>
                </div>
              </div>

              <div className="rounded-lg border p-4">
                <div className="flex items-center gap-3">
                  <div className="rounded-md border p-2">
                    <Brain className="h-5 w-5" />
                  </div>

                  <div>
                    <p className="text-sm text-muted-foreground">
                      نسبة المباريات التي لها توقعات
                    </p>

                    <p className="text-2xl font-bold tabular-nums">
                      {data.stats.fixtures > 0
                        ? `${(
                            (data.stats.predictions /
                              data.stats.fixtures) *
                            100
                          ).toFixed(1)}%`
                        : "0%"}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>حالة النظام</CardTitle>

            <CardDescription>
              حالة خدمة جمع البيانات
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="flex items-start gap-3 rounded-lg border p-3">
              <div className="rounded-md border p-2">
                <Server className="h-4 w-4" />
              </div>

              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium">خدمة Collector</p>

                  <span
                    className={`h-2 w-2 rounded-full ${
                      data.system.status === "online"
                        ? "bg-emerald-500"
                        : "bg-destructive"
                    }`}
                  />
                </div>

                <p className="text-sm text-muted-foreground">
                  {data.system.status === "online"
                    ? "متصلة وتعمل بصورة طبيعية"
                    : data.system.status}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 rounded-lg border p-3">
              <div className="rounded-md border p-2">
                <ShieldCheck className="h-4 w-4" />
              </div>

              <div className="min-w-0">
                <p className="font-medium">إصدار API</p>

                <p className="text-sm text-muted-foreground" dir="ltr">
                  v{data.system.version}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 rounded-lg border p-3">
              <div className="rounded-md border p-2">
                <RefreshCw className="h-4 w-4" />
              </div>

              <div className="min-w-0">
                <p className="font-medium">التحديث التلقائي</p>

                <p className="text-sm text-muted-foreground">
                  كل 30 ثانية
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
