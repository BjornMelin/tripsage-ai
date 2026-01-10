/**
 * @fileoverview Dashboard root layout (RSC shell) enforcing auth and providing the shared dashboard chrome.
 */

import { Suspense } from "react";
import { DashboardLayout } from "@/components/layouts/dashboard-layout";
import DashboardLoading from "./loading";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<DashboardLoading />}>
      <DashboardLayout>{children}</DashboardLayout>
    </Suspense>
  );
}
