/**
 * @fileoverview Public deployment health endpoint.
 */

import "server-only";

import { NextResponse } from "next/server";
import { nowIso } from "@/lib/security/random";

export const dynamic = "force-dynamic";

/**
 * Return a lightweight deployment health response for smoke checks.
 *
 * @returns JSON status without probing downstream services.
 */
export function GET(): NextResponse {
  return NextResponse.json(
    {
      service: "tripsage-ai",
      status: "ok",
      timestamp: nowIso(),
    },
    {
      headers: {
        "Cache-Control": "no-store",
      },
      status: 200,
    }
  );
}
