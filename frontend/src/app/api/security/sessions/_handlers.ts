/**
 * @fileoverview Security session handlers for listing and terminating sessions.
 */
import { NextResponse } from "next/server";
import type { TypedAdminSupabase } from "@/lib/supabase/admin";
import type { Database } from "@/lib/supabase/database.types";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const logger = createServerLogger("api.security.sessions");

/** Shape returned to the client for an active Supabase Auth session. */
export interface ActiveSessionResponse {
  id: string;
  device: string;
  browser: string;
  location: string;
  ipAddress: string;
  lastActivity: string;
  isCurrent: boolean;
}

/** Shape of a session row from the auth.sessions table. */
type SessionRow = Database["auth"]["Tables"]["sessions"]["Row"];

/** Decodes a base64url string to UTF-8 text. */
function decodeBase64Url(payload: string): string {
  const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
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

/** Returns the current session id from the user's Supabase session token. */
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
 * Maps a session row to an ActiveSessionResponse.
 *
 * @param row - The session row to map.
 * @param currentSessionId - The current session id.
 * @returns The mapped session response.
 */
function mapSessionRow(
  row: SessionRow,
  currentSessionId: string | null
): ActiveSessionResponse {
  const lastActivity =
    row.refreshed_at ?? row.updated_at ?? row.created_at ?? new Date().toISOString();
  return {
    browser: row.user_agent ?? "Unknown",
    device: row.user_agent ?? "Unknown device",
    id: row.id,
    ipAddress: getIpAddress(row.ip),
    isCurrent: currentSessionId === row.id,
    lastActivity,
    location: "Unknown",
  };
}

/**
 * Lists active sessions for a user, excluding expired records.
 *
 * @param params - The parameters for the list sessions handler.
 * @returns The list sessions response.
 */
export async function listSessionsHandler(params: {
  adminSupabase: TypedAdminSupabase;
  currentSessionId: string | null;
  userId: string;
}): Promise<NextResponse> {
  const { adminSupabase, currentSessionId, userId } = params;

  return await withTelemetrySpan(
    "security.sessions.list",
    { attributes: { userId } },
    async (span) => {
      const query = adminSupabase
        .schema("auth")
        .from("sessions")
        .select(
          "id, user_agent, ip, refreshed_at, updated_at, created_at, not_after, user_id, aal, factor_id, oauth_client_id, tag"
        )
        .eq("user_id", userId)
        .is("not_after", null)
        .order("refreshed_at", { ascending: false })
        .limit(50);

      const { data, error } = await query;
      if (error) {
        span.setAttribute("security.sessions.list.error", true);
        logger.error("sessions_list_failed", { error: error.message, userId });
        return NextResponse.json(
          { error: "failed_to_fetch_sessions" },
          { status: 500 }
        );
      }

      const sessions = (data ?? []).map((row) => mapSessionRow(row, currentSessionId));
      return NextResponse.json(sessions);
    }
  );
}

/**
 * Terminates a specific session owned by the user.
 *
 * @param params - The parameters for the terminate session handler.
 * @returns The terminate session response.
 */
export async function terminateSessionHandler(params: {
  adminSupabase: TypedAdminSupabase;
  sessionId: string;
  userId: string;
}): Promise<NextResponse> {
  const { adminSupabase, sessionId, userId } = params;

  return await withTelemetrySpan(
    "security.sessions.terminate",
    { attributes: { sessionId, userId } },
    async (span) => {
      const sessionQuery = adminSupabase
        .schema("auth")
        .from("sessions")
        .select("id")
        .eq("id", sessionId)
        .eq("user_id", userId)
        .maybeSingle();

      const { data: session, error: fetchError } = await sessionQuery;
      if (fetchError) {
        span.setAttribute("security.sessions.terminate.error", true);
        logger.error("session_lookup_failed", {
          error: fetchError.message,
          sessionId,
          userId,
        });
        return NextResponse.json({ error: "failed_to_fetch_session" }, { status: 500 });
      }

      if (!session) {
        return NextResponse.json({ error: "session_not_found" }, { status: 404 });
      }

      const deleteResult = await adminSupabase
        .schema("auth")
        .from("sessions")
        .delete()
        .eq("id", sessionId)
        .eq("user_id", userId);

      if (deleteResult.error) {
        span.setAttribute("security.sessions.terminate.error", true);
        logger.error("session_delete_failed", {
          error: deleteResult.error.message,
          sessionId,
          userId,
        });
        return NextResponse.json(
          { error: "failed_to_terminate_session" },
          { status: 500 }
        );
      }

      return new NextResponse(null, { status: 204 });
    }
  );
}
