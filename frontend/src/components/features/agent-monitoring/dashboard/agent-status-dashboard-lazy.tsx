"use client";

import { LoadingSpinner } from "@/components/ui/loading-spinner";
import dynamic from "next/dynamic";
import type { ComponentProps } from "react";

// Dynamically import the AgentStatusDashboard with loading fallback
const AgentStatusDashboard = dynamic(
  () =>
    import("./agent-status-dashboard").then((mod) => ({
      default: mod.AgentStatusDashboard,
    })),
  {
    loading: () => (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="text-sm text-muted-foreground mt-2">
            Loading agent dashboard...
          </p>
        </div>
      </div>
    ),
    ssr: false, // Disable SSR for this heavy component
  }
);

type AgentStatusDashboardProps = ComponentProps<typeof AgentStatusDashboard>;

export { AgentStatusDashboard };
export type { AgentStatusDashboardProps };
