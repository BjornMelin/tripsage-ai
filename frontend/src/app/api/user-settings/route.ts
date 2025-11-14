/**
 * @fileoverview User settings API for BYOK/Gateway consent.
 * Route: /api/user-settings
 * Methods: GET (read), POST (upsert allow_gateway_fallback)
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase";
import { getUserAllowGatewayFallback } from "@/lib/supabase/rpc";

export const dynamic = "force-dynamic";

/**
 * GET /api/user-settings
 * Retrieves user's gateway fallback preference setting.
 * Requires authenticated user session.
 * @returns NextResponse with allowGatewayFallback boolean or error
 */
export async function GET() {
  const supabase = await createServerSupabase();
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();
  if (error || !user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  try {
    const allowGatewayFallback = await getUserAllowGatewayFallback(user.id);
    return NextResponse.json({ allowGatewayFallback }, { status: 200 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/user-settings GET error:", { message });
    return NextResponse.json(
      { code: "INTERNAL_ERROR", error: "Internal server error" },
      { status: 500 }
    );
  }
}

import type { Database } from "@/lib/supabase/database.types";

/**
 * POST /api/user-settings
 * Updates user's gateway fallback preference setting.
 * Requires authenticated user session.
 * @param req - NextRequest containing allowGatewayFallback boolean in body
 * @returns NextResponse with success confirmation or error
 */
export async function POST(req: NextRequest) {
  const supabase = await createServerSupabase();
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();
  if (error || !user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  let allowGatewayFallback: unknown;
  try {
    const body = await req.json();
    allowGatewayFallback = body?.allowGatewayFallback;
  } catch (_parseErr) {
    return NextResponse.json(
      { code: "BAD_REQUEST", error: "Malformed JSON" },
      { status: 400 }
    );
  }
  if (typeof allowGatewayFallback !== "boolean") {
    return NextResponse.json(
      { code: "BAD_REQUEST", error: "allowGatewayFallback must be boolean" },
      { status: 400 }
    );
  }
  try {
    // Upsert row with owner RLS via SSR client
    type UserSettingsInsert = Database["public"]["Tables"]["user_settings"]["Insert"];
    // DB column names use snake_case by convention
    const payload: UserSettingsInsert = {
      allow_gateway_fallback: allowGatewayFallback,
      user_id: user.id,
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
    if (upsertError) throw upsertError;
    return NextResponse.json({ ok: true }, { status: 200 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/user-settings POST error:", { message });
    return NextResponse.json(
      { code: "INTERNAL_ERROR", error: "Internal server error" },
      { status: 500 }
    );
  }
}
