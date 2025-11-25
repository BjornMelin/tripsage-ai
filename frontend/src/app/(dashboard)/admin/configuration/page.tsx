/**
 * Admin Configuration Page
 *
 * Next.js page component for the configuration management interface.
 * Provides access to the ConfigurationManager component with proper authentication.
 */

import type { AgentType } from "@schemas/configuration";
import type { Metadata } from "next";
import { Suspense } from "react";
import { fetchAgentBundle } from "@/components/admin/configuration-actions";
import ConfigurationManager from "@/components/admin/configuration-manager";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

export const metadata: Metadata = {
  description:
    "Manage AI agent configurations, monitor performance, and track version history",
  title: "Agent Configuration - TripSage Admin",
};

const DEFAULT_AGENT: AgentType = "budgetAgent";

export default async function ConfigurationPage() {
  const initial = await fetchAgentBundle(DEFAULT_AGENT);

  return (
    <div className="container mx-auto py-6">
      <Suspense
        fallback={
          <div className="flex items-center justify-center min-h-[400px]">
            <LoadingSpinner size="lg" />
          </div>
        }
      >
        <ConfigurationManager
          initialAgent={DEFAULT_AGENT}
          initialConfig={initial.config}
          initialMetrics={initial.metrics}
          initialVersions={initial.versions}
        />
      </Suspense>
    </div>
  );
}
