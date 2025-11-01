// caching handled at app level via cacheComponents; no per-file directive
import { Suspense } from "react";
import { DashboardLayout } from "@/components/layouts/dashboard-layout";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={null}>
      <DashboardLayout>{children}</DashboardLayout>
    </Suspense>
  );
}
