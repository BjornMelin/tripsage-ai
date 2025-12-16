/**
 * @fileoverview Server-only security session data accessors shared by routes and RSC.
 */

import "server-only";

import { type ActiveSession, activeSessionSchema } from "@schemas/security";
import { nowIso } from "@/lib/security/random";
import type { TypedAdminSupabase } from "@/lib/supabase/admin";
import type { Database } from "@/lib/supabase/database.types";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const logger = createServerLogger("security.sessions");

/** Shape of a session row from the auth.sessions table. */
type SessionRow = Database["auth"]["Tables"]["sessions"]["Row"];

type SessionRowForMapping = Pick<
  SessionRow,
  "created_at" | "id" | "ip" | "refreshed_at" | "updated_at" | "user_agent"
>;

export class SessionsListError extends Error {
  public override readonly cause?: unknown;

  constructor(message: string, cause?: unknown) {
    super(message);
    this.name = "SessionsListError";
    this.cause = cause;
  }
}

/** Decodes a base64url string to UTF-8 text. */
function decodeBase64Url(payload: string): string {
  const normalized = payload.replaceAll("-", "+").replaceAll("_", "/");
  const padLength = (4 - (normalized.length % 4)) % 4;
  const padded = `${normalized}${"=".repeat(padLength)}`;
  return Buffer.from(padded, "base64").toString("utf8");
}

/** Extracts the session_id claim from a Supabase access token, if present. */
function parseSessionIdFromToken(
  accessToken: string | null | undefined
): string | null {
  if (!accessToken) return null;
  const parts = accessToken.split(".");
  if (parts.length !== 3) return null;
  try {
    const payload = JSON.parse(decodeBase64Url(parts[1] ?? ""));
    const sessionId = payload?.session_id ?? payload?.sessionId;
    return typeof sessionId === "string" ? sessionId : null;
  } catch (error) {
    logger.warn("session_id_parse_failed", {
      error: error instanceof Error ? error.message : "unknown_error",
    });
    return null;
  }
}

/** Returns the current session id from the authenticated Supabase session token. */
export async function getCurrentSessionId(
  supabase: TypedServerSupabase
): Promise<string | null> {
  try {
    const { data, error } = await supabase.auth.getSession();
    if (error) {
      logger.warn("session_fetch_failed", { error: error.message });
      return null;
    }
    return parseSessionIdFromToken(data.session?.access_token);
  } catch (error) {
    logger.error("session_fetch_exception", {
      error: error instanceof Error ? error.message : "unknown_error",
    });
    return null;
  }
}

/**
 * Extracts the IP address from a session row.
 *
 * @param ipValue - The IP address value to extract.
 * @returns The IP address string or "Unknown" if not found.
 */
function getIpAddress(ipValue: unknown): string {
  if (typeof ipValue === "string") return ipValue;
  if (
    ipValue &&
    typeof ipValue === "object" &&
    "address" in (ipValue as Record<string, unknown>)
  ) {
    const address = (ipValue as { address?: unknown }).address;
    if (typeof address === "string") return address;
  }
  return "Unknown";
}

/**
 * Maps a session row to an ActiveSession DTO.
 *
 * @param row - The session row to map.
 * @param currentSessionId - The current session id.
 * @returns The mapped session DTO.
 */
export function mapSessionRow(
  row: SessionRowForMapping,
  currentSessionId: string | null
): ActiveSession {
  const lastActivity = row.refreshed_at ?? row.updated_at ?? row.created_at;
  if (!lastActivity) {
    logger.warn("session_missing_activity_timestamp", {
      observedAt: nowIso(),
      sessionId: row.id,
    });
  }
  return {
    browser: row.user_agent ?? "Unknown",
    device: row.user_agent ?? "Unknown device",
    id: row.id,
    ipAddress: getIpAddress(row.ip),
    isCurrent: currentSessionId === row.id,
    lastActivity: lastActivity ?? "Unknown",
    location: "Unknown",
  };
}

/**
 * Lists active sessions for a user, excluding expired records.
 *
 * @param adminSupabase - Admin Supabase client.
 * @param userId - User ID to list sessions for.
 * @param opts - Options including current session id.
 * @returns Active sessions as DTOs.
 */
export async function listActiveSessions(
  adminSupabase: TypedAdminSupabase,
  userId: string,
  opts: { currentSessionId?: string | null } = {}
): Promise<ActiveSession[]> {
  const currentSessionId = opts.currentSessionId ?? null;

  return await withTelemetrySpan(
    "security.sessions.list",
    { attributes: { userId } },
    async (span) => {
      const query = adminSupabase
        .schema("auth")
        .from("sessions")
        .select("id, user_agent, ip, refreshed_at, updated_at, created_at")
        .eq("user_id", userId)
        .is("not_after", null)
        .order("refreshed_at", { ascending: false })
        .order("updated_at", { ascending: false })
        .order("created_at", { ascending: false })
        .limit(50);

      const { data, error } = await query;
      if (error) {
        span.setAttribute("security.sessions.list.error", true);
        logger.error("sessions_list_failed", { error: error.message, userId });
        throw new SessionsListError("sessions_list_failed", error);
      }

      const sessions = (data ?? []).map((row) => mapSessionRow(row, currentSessionId));
      const parsed = activeSessionSchema.array().safeParse(sessions);
      if (!parsed.success) {
        span.setAttribute("security.sessions.list.invalid_shape", true);
        logger.error("sessions_list_invalid_shape", {
          issues: parsed.error.issues,
          userId,
        });
        throw new SessionsListError("invalid_sessions_shape", parsed.error);
      }
      return parsed.data;
    }
  );
}
