/**
 * @fileoverview Dashboard root layout (RSC shell) enforcing auth and providing the
 * shared dashboard chrome.
 *
 * Caching is handled at the app level via `cacheComponents`; this layout intentionally
 * does not opt into per-file caching directives because it relies on authenticated
 * user context.
 */

import { Suspense } from "react";
import { DashboardLayout } from "@/components/layouts/dashboard-layout";
import { requireUser } from "@/lib/auth/server";
import DashboardLoading from "./loading";

export default async function Layout({ children }: { children: React.ReactNode }) {
  // Enforce Supabase SSR auth for all dashboard routes.
  await requireUser();

  return (
    <Suspense fallback={<DashboardLoading />}>
      <DashboardLayout>{children}</DashboardLayout>
    </Suspense>
  );
}
