/**
 * @fileoverview Shared security data accessors for events and metrics.
 */

import {
  type ActiveSession,
  activeSessionSchema,
  type SecurityEvent,
  type SecurityMetrics,
  securityEventSchema,
  securityMetricsSchema,
} from "@schemas/security";
import type { TypedAdminSupabase } from "@/lib/supabase/admin";

/** Audit log row type. */
type AuditLogRow = {
  id: string;
  createdAt: string;
  ipAddress: string | null;
  payload: Record<string, unknown>;
};

/** 24 hours in milliseconds. */
const HOURS_24_MS = 24 * 60 * 60 * 1000;

/**
 * Maps an audit log action to a security event type.
 *
 * @param action - The audit log action to map.
 * @returns The security event type.
 */
const mapEventType = (action?: string): SecurityEvent["type"] => {
  switch (action) {
    case "login":
      return "login_success";
    case "login_failure":
      return "login_failure";
    case "logout":
      return "logout";
    case "mfa_enroll":
      return "mfa_enabled";
    case "password_update":
      return "password_change";
    default:
      return "suspicious_activity";
  }
};

const mapRisk = (type: SecurityEvent["type"]): SecurityEvent["riskLevel"] => {
  if (type === "login_failure" || type === "suspicious_activity") return "high";
  if (type === "password_change" || type === "mfa_enabled") return "medium";
  return "low";
};

/**
 * Get the security events for a user.
 *
 * @param adminSupabase - The admin Supabase client.
 * @param userId - The ID of the user to get the security events for.
 * @returns The security events.
 */
export async function getUserSecurityEvents(
  adminSupabase: TypedAdminSupabase,
  userId: string
): Promise<SecurityEvent[]> {
  const { data, error } = await adminSupabase
    .schema("auth")
    .from("audit_log_entries")
    .select("id, created_at, ip_address, payload")
    .eq("payload->>user_id", userId)
    .order("created_at", { ascending: false })
    .limit(50);

  if (error) {
    throw new Error("failed_to_fetch_events");
  }

  const rows = (data ?? []).map((row) => {
    const record = row as Record<string, unknown>;
    return {
      createdAt: record.created_at as string,
      id: record.id as string,
      ipAddress: (record.ip_address as string | null | undefined) ?? null,
      payload: (record.payload as Record<string, unknown>) ?? {},
    };
  }) as AuditLogRow[];
  const events = rows.map((row) => {
    const action = (row.payload?.action as string | undefined) ?? undefined;
    const type = mapEventType(action);
    return {
      description: action ?? "activity detected",
      device: (row.payload?.user_agent as string | undefined) ?? undefined,
      id: row.id,
      ipAddress: row.ipAddress ?? "Unknown",
      location: undefined,
      riskLevel: mapRisk(type),
      timestamp: row.createdAt,
      type,
    };
  });

  const parsed = securityEventSchema.array().safeParse(events);
  if (!parsed.success) {
    throw new Error("invalid_event_shape");
  }
  return parsed.data;
}

/**
 * Get the security metrics for a user.
 *
 * @param adminSupabase - The admin Supabase client.
 * @param userId - The ID of the user to get the security metrics for.
 * @returns The security metrics.
 */
export async function getUserSecurityMetrics(
  adminSupabase: TypedAdminSupabase,
  userId: string
): Promise<SecurityMetrics> {
  const since = new Date(Date.now() - HOURS_24_MS).toISOString();

  const results = await Promise.allSettled([
    adminSupabase
      .schema("auth")
      .from("audit_log_entries")
      .select("created_at")
      .eq("payload->>user_id", userId)
      .eq("payload->>action", "login")
      .order("created_at", { ascending: false })
      .limit(1),
    adminSupabase
      .schema("auth")
      .from("audit_log_entries")
      .select("*", { count: "exact", head: true })
      .eq("payload->>user_id", userId)
      .eq("payload->>action", "login")
      .eq("payload->>success", "false")
      .gte("created_at", since),
    adminSupabase
      .schema("auth")
      .from("sessions")
      .select("id", { count: "exact", head: true })
      .eq("user_id", userId)
      .is("not_after", null),
    adminSupabase
      .schema("auth")
      .from("mfa_factors")
      .select("id")
      .eq("user_id", userId)
      .eq("status", "verified"),
    adminSupabase
      .schema("auth")
      .from("identities")
      .select("provider")
      .eq("user_id", userId)
      .neq("provider", "email"),
  ]);

  const [loginRowsRes, failedRes, sessionRes, mfaRes, identitiesRes] = results.map(
    (r) => (r.status === "fulfilled" ? r.value : { count: 0, data: [], error: null })
  ) as Array<{ data?: unknown; count?: number | null; error?: unknown }>;

  const loginRows =
    (loginRowsRes.data as Array<Record<string, unknown>> | undefined)?.map(
      (row) => row.created_at as string
    ) ?? [];
  const failedLoginAttempts = failedRes.count ?? 0;
  const activeSessions = sessionRes.count ?? 0;
  const oauthConnections = (
    (identitiesRes.data as Array<{ provider: string }> | undefined) ?? []
  )
    .map((i) => i.provider)
    .filter(Boolean);
  const mfaEnabled = ((mfaRes.data as Array<unknown>) ?? []).length > 0;

  const lastLogin = loginRows[0] ?? "never";
  const trustedDevices = activeSessions;

  const MfaBonus = 20;
  const NoFailedLoginBonus = 10;
  const SessionCountBonus = 10;
  const OauthBonus = 10;

  let securityScore = 50;
  if (mfaEnabled) securityScore += MfaBonus;
  if (failedLoginAttempts === 0) securityScore += NoFailedLoginBonus;
  if (activeSessions <= 3) securityScore += SessionCountBonus;
  if (oauthConnections.length > 0) securityScore += OauthBonus;
  if (securityScore > 100) securityScore = 100;

  const metrics = {
    activeSessions,
    failedLoginAttempts,
    lastLogin,
    oauthConnections,
    securityScore,
    trustedDevices,
  };

  const parsed = securityMetricsSchema.safeParse(metrics);
  if (!parsed.success) {
    throw new Error("invalid_metrics_shape");
  }

  return parsed.data;
}

/**
 * Get the sessions for a user.
 *
 * @param adminSupabase - The admin Supabase client.
 * @param userId - The ID of the user to get the sessions for.
 * @returns The sessions.
 */
export async function getUserSessions(
  adminSupabase: TypedAdminSupabase,
  userId: string
): Promise<ActiveSession[]> {
  const { data, error } = await adminSupabase
    .schema("auth")
    .from("sessions")
    .select("id, user_agent, ip, refreshed_at, updated_at, created_at, not_after")
    .eq("user_id", userId)
    .is("not_after", null)
    .order("refreshed_at", { ascending: false })
    .limit(50);

  if (error) {
    throw new Error("failed_to_fetch_sessions");
  }

  const rows = data ?? [];
  const mapped = rows.map((row) => {
    const record = row as Record<string, unknown>;
    // biome-ignore lint/complexity/useLiteralKeys: upstream column names are snake_case
    const userAgent = record["user_agent"] as string | null | undefined;
    // biome-ignore lint/complexity/useLiteralKeys: upstream column names are snake_case
    const refreshedAt = record["refreshed_at"] as string | null | undefined;
    // biome-ignore lint/complexity/useLiteralKeys: upstream column names are snake_case
    const updatedAt = record["updated_at"] as string | null | undefined;
    // biome-ignore lint/complexity/useLiteralKeys: upstream column names are snake_case
    const createdAt = record["created_at"] as string | null | undefined;
    return {
      browser: userAgent ?? "Unknown",
      device: userAgent ?? "Unknown device",
      id: record.id as string,
      ipAddress: (record.ip as string | null | undefined) ?? "Unknown",
      isCurrent: false,
      lastActivity: refreshedAt ?? updatedAt ?? createdAt ?? new Date().toISOString(),
      location: "Unknown",
    };
  });

  const parsed = activeSessionSchema.array().safeParse(mapped);
  if (!parsed.success) {
    throw new Error("invalid_sessions_shape");
  }
  return parsed.data;
}
