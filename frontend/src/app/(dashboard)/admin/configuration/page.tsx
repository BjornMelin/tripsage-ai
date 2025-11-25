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
import { createServerLogger } from "@/lib/telemetry/logger";

export const metadata: Metadata = {
  description:
    "Manage AI agent configurations, monitor performance, and track version history",
  title: "Agent Configuration - TripSage Admin",
};

const DEFAULT_AGENT: AgentType = "budgetAgent";
const logger = createServerLogger("admin.configuration.page");

export default async function ConfigurationPage() {
  let initial: Awaited<ReturnType<typeof fetchAgentBundle>>;
  try {
    initial = await fetchAgentBundle(DEFAULT_AGENT);
  } catch (error) {
    logger.error("failed to fetch default agent bundle", {
      agentType: DEFAULT_AGENT,
      error,
    });

    return (
      <div className="container mx-auto py-6">
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-destructive-foreground">
          <p className="font-semibold">Unable to load agent configuration.</p>
          <p className="text-sm text-destructive-foreground/80">
            Please try again or contact an administrator if the issue persists.
          </p>
        </div>
      </div>
    );
  }

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
