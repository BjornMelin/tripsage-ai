/**
 * @fileoverview User settings API route handlers.
 *
 * Handles BYOK/Gateway consent preferences. Methods: GET (read),
 * POST (upsert allow_gateway_fallback).
 */

import "server-only";

// Security: Prevent caching of user-specific settings per ADR-0024.
// With Cache Components enabled, route handlers are dynamic by default.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching. No 'use cache' directives are present.

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, parseJsonBody } from "@/lib/api/route-helpers";
import { getUserAllowGatewayFallback } from "@/lib/supabase/rpc";

/**
 * Retrieves the user's gateway fallback preference setting.
 *
 * Requires authentication.
 *
 * @returns Promise resolving to NextResponse with allowGatewayFallback boolean.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "user-settings:get",
  telemetry: "user-settings.get",
})(async (_req, { user }) => {
  // auth: true guarantees user is authenticated
  const userId = user?.id ?? "";
  const allowGatewayFallback = await getUserAllowGatewayFallback(userId);
  return NextResponse.json({ allowGatewayFallback });
});

import type { Database } from "@/lib/supabase/database.types";

/**
 * Updates the user's gateway fallback preference setting.
 *
 * Requires authentication. Body must contain `allowGatewayFallback` boolean.
 *
 * @param req NextRequest containing allowGatewayFallback boolean in body.
 * @returns Promise resolving to NextResponse with success confirmation or error.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "user-settings:update",
  telemetry: "user-settings.update",
})(async (req: NextRequest, { user, supabase }) => {
  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return errorResponse({
      error: "bad_request",
      reason: "Malformed JSON",
      status: 400,
    });
  }
  const body = parsed.body as { allowGatewayFallback?: unknown };
  const allowGatewayFallback = body?.allowGatewayFallback;
  if (typeof allowGatewayFallback !== "boolean") {
    return errorResponse({
      error: "bad_request",
      reason: "allowGatewayFallback must be boolean",
      status: 400,
    });
  }

  // auth: true guarantees user is authenticated
  const userId = user?.id ?? "";

  // Upsert row with owner RLS via SSR client
  type UserSettingsInsert = Database["public"]["Tables"]["user_settings"]["Insert"];
  // DB column names use snake_case by convention
  const payload: UserSettingsInsert = {
    allow_gateway_fallback: allowGatewayFallback,
    user_id: userId,
  };
  const { error: upsertError } = await (
    supabase as unknown as {
      from: (table: string) => {
        upsert: (
          values: Record<string, unknown>,
          options?: { onConflict?: string; ignoreDuplicates?: boolean }
        ) => Promise<{ error: unknown | null }>;
      };
    }
  )
    .from("user_settings")
    .upsert(payload as unknown as Record<string, unknown>, {
      ignoreDuplicates: false,
      onConflict: "user_id",
    });
  if (upsertError) {
    throw upsertError;
  }
  return NextResponse.json({ ok: true });
});
