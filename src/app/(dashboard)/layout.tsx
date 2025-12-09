// caching handled at app level via cacheComponents; no per-file directive
import { Suspense } from "react";
import { DashboardLayout } from "@/components/layouts/dashboard-layout";
import { requireUser } from "@/lib/auth/server";

export default async function Layout({ children }: { children: React.ReactNode }) {
  // Enforce Supabase SSR auth for all dashboard routes.
  await requireUser();

  return (
    <Suspense fallback={null}>
      <DashboardLayout>{children}</DashboardLayout>
    </Suspense>
  );
}
