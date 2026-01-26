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
import { extractErrorMessage } from "@/lib/errors/error-message";
import type { TypedAdminSupabase } from "@/lib/supabase/admin";
import { getMany } from "@/lib/supabase/typed-helpers";

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
  const { data, error } = await getMany(
    adminSupabase,
    "audit_log_entries",
    (qb) => qb.eq("payload->>user_id", userId),
    {
      ascending: false,
      limit: 50,
      orderBy: "created_at",
      schema: "auth",
      select: "id, created_at, ip_address, payload",
      validate: false,
    }
  );

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
 * @throws Error when one or more queries fail. Message format:
 * `failed_to_fetch_security_metrics:<label>:<message>|...` with
 * pipe-separated labels: `login_rows`, `failed_logins`, `sessions`,
 * `mfa_factors`, `identities`.
 */
export async function getUserSecurityMetrics(
  adminSupabase: TypedAdminSupabase,
  userId: string
): Promise<SecurityMetrics> {
  const since = new Date(Date.now() - HOURS_24_MS).toISOString();

  const [loginRowsRes, failedRes, sessionRes, mfaRes, identitiesRes] =
    await Promise.all([
      getMany(
        adminSupabase,
        "audit_log_entries",
        (qb) => qb.eq("payload->>user_id", userId).eq("payload->>action", "login"),
        {
          ascending: false,
          limit: 1,
          orderBy: "created_at",
          schema: "auth",
          select: "created_at",
          validate: false,
        }
      ),
      getMany(
        adminSupabase,
        "audit_log_entries",
        (qb) =>
          qb
            .eq("payload->>user_id", userId)
            .eq("payload->>action", "login")
            .eq("payload->>success", "false")
            .gte("created_at", since),
        {
          count: "exact",
          limit: 1,
          schema: "auth",
          select: "id",
          validate: false,
        }
      ),
      getMany(
        adminSupabase,
        "sessions",
        (qb) => qb.eq("user_id", userId).is("not_after", null),
        {
          count: "exact",
          limit: 1,
          schema: "auth",
          select: "id",
          validate: false,
        }
      ),
      getMany(
        adminSupabase,
        "mfa_factors",
        (qb) => qb.eq("user_id", userId).eq("status", "verified"),
        {
          schema: "auth",
          select: "id",
          validate: false,
        }
      ),
      getMany(
        adminSupabase,
        "identities",
        (qb) => qb.eq("user_id", userId).neq("provider", "email"),
        {
          schema: "auth",
          select: "provider",
          validate: false,
        }
      ),
    ]);

  const errors = [
    { error: loginRowsRes.error, label: "login_rows" },
    { error: failedRes.error, label: "failed_logins" },
    { error: sessionRes.error, label: "sessions" },
    { error: mfaRes.error, label: "mfa_factors" },
    { error: identitiesRes.error, label: "identities" },
  ].filter(
    (entry): entry is { label: string; error: NonNullable<typeof entry.error> } =>
      Boolean(entry.error)
  );

  if (errors.length > 0) {
    const details = errors.map(
      ({ label, error }) => `${label}:${extractErrorMessage(error)}`
    );
    throw new Error(`failed_to_fetch_security_metrics:${details.join("|")}`);
  }

  const safeLoginRowsRes = loginRowsRes;
  const safeFailedRes = failedRes;
  const safeSessionRes = sessionRes;
  const safeMfaRes = mfaRes;
  const safeIdentitiesRes = identitiesRes;

  const loginRows =
    (safeLoginRowsRes.data as Array<Record<string, unknown>> | undefined)?.map(
      (row) => row.created_at as string
    ) ?? [];
  const failedLoginAttempts = safeFailedRes.count ?? 0;
  const activeSessions = safeSessionRes.count ?? 0;
  const oauthConnections = (
    (safeIdentitiesRes.data as Array<{ provider: string }> | undefined) ?? []
  )
    .map((i) => i.provider)
    .filter(Boolean);
  const mfaEnabled = ((safeMfaRes.data as Array<unknown>) ?? []).length > 0;

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
  const { data, error } = await getMany(
    adminSupabase,
    "sessions",
    (qb) => qb.eq("user_id", userId).is("not_after", null),
    {
      ascending: false,
      limit: 50,
      orderBy: "refreshed_at",
      schema: "auth",
      select: "id, user_agent, ip, refreshed_at, updated_at, created_at, not_after",
      validate: false,
    }
  );

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
