/**
 * @fileoverview API route for reading/writing per-user gateway fallback settings.
 */

import "server-only";

// Security: Prevent caching of user-specific settings per ADR-0024.
// With Cache Components enabled, route handlers are dynamic by default.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching. No 'use cache' directives are present.

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import {
  errorResponse,
  parseJsonBody,
  requireUserId,
  validateSchema,
} from "@/lib/api/route-helpers";
import type { TablesInsert } from "@/lib/supabase/database.types";
import { getUserAllowGatewayFallback } from "@/lib/supabase/rpc";

const updateUserSettingsSchema = z.strictObject({
  allowGatewayFallback: z.boolean({
    error: "allowGatewayFallback must be a boolean",
  }),
});

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
  const result = requireUserId(user);
  if (!result.ok) return result.error;
  const userId = result.data;
  const allowGatewayFallback = await getUserAllowGatewayFallback(userId);
  return NextResponse.json({ allowGatewayFallback });
});

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
  const result = requireUserId(user);
  if (!result.ok) return result.error;
  const userId = result.data;

  const parsed = await parseJsonBody(req);
  if (!parsed.ok) return parsed.error;

  const validation = validateSchema(updateUserSettingsSchema, parsed.data);
  if (!validation.ok) return validation.error;
  const { allowGatewayFallback } = validation.data;

  // Upsert row with owner RLS via SSR client
  type UserSettingsInsert = TablesInsert<"user_settings">;
  // DB column names use snake_case by convention
  const payload: UserSettingsInsert = {
    allow_gateway_fallback: allowGatewayFallback,
    user_id: userId,
  };
  const { error: upsertError } = await supabase.from("user_settings").upsert(payload, {
    ignoreDuplicates: false,
    onConflict: "user_id",
  });
  if (upsertError) {
    return errorResponse({
      err: upsertError,
      error: "internal",
      reason: "Failed to update user settings",
      status: 500,
    });
  }
  return NextResponse.json({ ok: true });
});
