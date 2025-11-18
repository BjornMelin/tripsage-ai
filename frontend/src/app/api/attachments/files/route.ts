/**
 * @fileoverview API route for fetching attachment files with pagination support.
 * Provides a proxy endpoint to the backend API for retrieving user attachment files.
 */

"use cache: private";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { getServerEnvVarWithFallback } from "@/lib/env/server";

function getBackendApiUrl(): string {
  return (
    getServerEnvVarWithFallback("BACKEND_API_URL", "http://localhost:8001") ??
    "http://localhost:8001"
  );
}

/**
 * Retrieves attachment files with optional pagination parameters.
 *
 * @param req - The Next.js request object containing query parameters.
 * @param routeContext - Route context from withApiGuards
 * @returns A JSON response with attachment files data or an error response.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "attachments:files",
  telemetry: "attachments.files.read",
})(async (req: NextRequest) => {
  // Forward Authorization when present
  const authHeader = req.headers.get("authorization");

  // Preserve pagination query params
  const { searchParams } = req.nextUrl;
  const qs = searchParams.toString();
  const url = `${getBackendApiUrl()}/api/attachments/files${qs ? `?${qs}` : ""}`;

  const response = await fetch(url, {
    headers: authHeader ? { authorization: authHeader } : undefined,
    method: "GET",
    // Tag reads so uploads can revalidate via revalidateTag('attachments', 'max')
    next: { tags: ["attachments"] },
  });

  const data = await response.json();
  if (!response.ok) {
    return NextResponse.json(
      { error: data?.detail || "Failed to fetch attachments" },
      { status: response.status }
    );
  }

  return NextResponse.json(data, { status: 200 });
});
