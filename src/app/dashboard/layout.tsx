/**
 * @fileoverview Dashboard root layout (RSC shell) enforcing auth and providing the shared dashboard chrome.
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
