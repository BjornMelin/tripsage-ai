/**
 * @fileoverview Server-first security dashboard rendering live security data.
 */

import type { SecurityEvent } from "@schemas/security";
import { DefaultMetrics } from "@schemas/security";
import {
  ActivityIcon,
  AlertTriangleIcon,
  CheckCircle2Icon,
  LockIcon,
  MonitorIcon,
  ShieldIcon,
  UserCheckIcon,
} from "lucide-react";
import type React from "react";
import {
  ActiveSessionsList,
  ConnectionsSummary,
  SecurityEventsList,
} from "@/components/features/security/security-dashboard-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { getUserSecurityEvents, getUserSecurityMetrics } from "@/lib/security/service";
import { getCurrentSessionId, listActiveSessions } from "@/lib/security/sessions";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { createServerSupabase, getCurrentUser } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";

const SecurityDashboardLogger = createServerLogger("security.dashboard");

/**
 * Get the security data for the current user.
 *
 * @returns The security data.
 */
async function GetSecurityData() {
  const supabase = await createServerSupabase();
  const { user, error } = await getCurrentUser(supabase);
  if (error) {
    throw error;
  }
  if (!user) {
    throw new Error("unauthorized");
  }

  const adminSupabase = createAdminSupabase();

  const [eventsResult, metricsResult, sessionsResult] = await Promise.allSettled([
    getUserSecurityEvents(adminSupabase, user.id),
    getUserSecurityMetrics(adminSupabase, user.id),
    getCurrentSessionId(supabase).then((currentSessionId) =>
      listActiveSessions(adminSupabase, user.id, { currentSessionId })
    ),
  ]);

  if (eventsResult.status === "rejected") {
    SecurityDashboardLogger.warn("security_dashboard_events_fetch_failed", {
      error:
        eventsResult.reason instanceof Error
          ? eventsResult.reason.message
          : "unknown_error",
      userId: user.id,
    });
  }
  if (metricsResult.status === "rejected") {
    SecurityDashboardLogger.warn("security_dashboard_metrics_fetch_failed", {
      error:
        metricsResult.reason instanceof Error
          ? metricsResult.reason.message
          : "unknown_error",
      userId: user.id,
    });
  }
  if (sessionsResult.status === "rejected") {
    SecurityDashboardLogger.warn("security_dashboard_sessions_fetch_failed", {
      error:
        sessionsResult.reason instanceof Error
          ? sessionsResult.reason.message
          : "unknown_error",
      userId: user.id,
    });
  }

  return {
    events: eventsResult.status === "fulfilled" ? eventsResult.value : [],
    metrics:
      metricsResult.status === "fulfilled" ? metricsResult.value : DefaultMetrics,
    sessions: sessionsResult.status === "fulfilled" ? sessionsResult.value : [],
  };
}

/** The risk color for each security event risk level. */
const RiskColor: Record<SecurityEvent["riskLevel"], string> = {
  high: "text-red-600",
  low: "text-green-600",
  medium: "text-yellow-600",
};

/**
 * The security dashboard component.
 *
 * @returns The security dashboard component.
 */
export async function SecurityDashboard() {
  const { events, metrics, sessions } = await GetSecurityData();

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldIcon className="h-5 w-5" />
            Security Overview
          </CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricTile
            label="Security Score"
            value={metrics.securityScore.toString()}
            icon={<CheckCircle2Icon className="h-4 w-4" />}
          />
          <MetricTile
            label="Active Sessions"
            value={metrics.activeSessions.toString()}
            icon={<MonitorIcon className="h-4 w-4" />}
          />
          <MetricTile
            label="Failed Logins (24h)"
            value={metrics.failedLoginAttempts.toString()}
            icon={<AlertTriangleIcon className="h-4 w-4" />}
          />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ActivityIcon className="h-5 w-5" />
              Recent Events
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <SecurityEventsList events={events} riskColor={RiskColor} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserCheckIcon className="h-5 w-5" />
              Active Sessions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <ActiveSessionsList sessions={sessions} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LockIcon className="h-5 w-5" />
            Connections
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <ConnectionsSummary metrics={metrics} />
        </CardContent>
      </Card>
      <Separator />
    </div>
  );
}

/** Metric tile props. */
function MetricTile({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="border rounded-md p-4 flex items-center gap-3">
      {icon}
      <div>
        <div className="text-sm text-muted-foreground">{label}</div>
        <div className="text-xl font-semibold">{value}</div>
      </div>
    </div>
  );
}
