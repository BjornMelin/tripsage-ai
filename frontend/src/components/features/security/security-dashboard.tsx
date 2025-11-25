/**
 * @fileoverview Server-first security dashboard rendering live security data.
 */

import {
  type ActiveSession,
  activeSessionSchema,
  type SecurityEvent,
  type SecurityMetrics,
  securityEventSchema,
  securityMetricsSchema,
} from "@schemas/security";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Monitor,
  Shield,
  UserCheck,
} from "lucide-react";
import { cookies, headers } from "next/headers";
import type React from "react";
import type { ZodTypeAny } from "zod";
import {
  ActiveSessionsList,
  ConnectionsSummary,
  SecurityEventsList,
} from "@/components/features/security/security-dashboard-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

/**
 * Build a cookie header string from the cookie store.
 *
 * @returns The cookie header string.
 */
const BuildCookieHeader = async () => {
  const cookieStore = await cookies();
  return cookieStore
    .getAll()
    .map((c: { name: string; value: string }) => `${c.name}=${c.value}`)
    .join("; ");
};

/**
 * Fetch data from the API and parse it using a Zod schema.
 *
 * @param path - The path to fetch the data from.
 * @param schema - The Zod schema to parse the data with.
 * @returns The parsed data.
 */
const ApiFetch = async <T,>(path: string, schema: ZodTypeAny) => {
  const headerStore = await headers();
  const host = headerStore.get("x-forwarded-host") ?? headerStore.get("host");
  const protocol = headerStore.get("x-forwarded-proto") ?? "http";
  const base = host ? `${protocol}://${host}` : "";
  const response = await fetch(`${base}${path}`, {
    cache: "no-store",
    headers: {
      cookie: await BuildCookieHeader(),
    },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch ${path}: ${response.status}`);
  }
  const json = (await response.json()) as unknown;
  const parsed = schema.safeParse(json);
  if (!parsed.success) {
    throw new Error(`Invalid shape from ${path}`);
  }
  return parsed.data as T;
};

/**
 * Get the security data from the API.
 *
 * @returns The security data.
 */
async function GetSecurityData() {
  const [events, metrics, sessions] = await Promise.all([
    ApiFetch<SecurityEvent[]>("/api/security/events", securityEventSchema.array()),
    ApiFetch<SecurityMetrics>("/api/security/metrics", securityMetricsSchema),
    ApiFetch<ActiveSession[]>("/api/security/sessions", activeSessionSchema.array()),
  ]);
  return { events, metrics, sessions };
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
            <Shield className="h-5 w-5" />
            Security Overview
          </CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricTile
            label="Security Score"
            value={metrics.securityScore.toString()}
            icon={<CheckCircle2 className="h-4 w-4" />}
          />
          <MetricTile
            label="Active Sessions"
            value={metrics.activeSessions.toString()}
            icon={<Monitor className="h-4 w-4" />}
          />
          <MetricTile
            label="Failed Logins (24h)"
            value={metrics.failedLoginAttempts.toString()}
            icon={<AlertTriangle className="h-4 w-4" />}
          />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
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
              <UserCheck className="h-5 w-5" />
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
            <Lock className="h-5 w-5" />
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
