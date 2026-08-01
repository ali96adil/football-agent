import AppShell from "@/components/layout/app-shell";
import { ProductGuard } from "@/components/layout/product-guard";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <ProductGuard><AppShell>{children}</AppShell></ProductGuard>;
}
