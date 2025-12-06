/**
 * @fileoverview Attachment files listing endpoint with Upstash Redis caching.
 *
 * Proxies to backend API with per-user response caching via Upstash Redis.
 * Cache TTL: 2 minutes. Invalidated when files are uploaded/deleted.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { requireUserId } from "@/lib/api/route-helpers";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import { getServerEnvVarWithFallback } from "@/lib/env/server";

/** Cache TTL for attachment listings (2 minutes). */
const CACHE_TTL_SECONDS = 120;

/** Returns backend API URL from environment or default. */
function getBackendApiUrl(): string {
  return (
    getServerEnvVarWithFallback("BACKEND_API_URL", "http://localhost:8001") ??
    "http://localhost:8001"
  );
}

/**
 * Builds cache key for attachment file listings.
 *
 * @param userId - Authenticated user ID.
 * @param queryString - URL query string for pagination.
 * @returns Redis cache key.
 */
function buildCacheKey(userId: string, queryString: string): string {
  return `attachments:files:${userId}:${queryString || "default"}`;
}

/**
 * GET /api/attachments/files
 *
 * Lists user attachment files with pagination support.
 * Response cached per-user in Redis with 2-minute TTL.
 *
 * @param req - Request with optional pagination query params.
 * @returns JSON array of attachment metadata or error.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "attachments:files",
  telemetry: "attachments.files.read",
})(async (req: NextRequest, { user, supabase }) => {
  const result = requireUserId(user);
  if ("error" in result) return result.error;
  const { userId } = result;
  const { searchParams } = req.nextUrl;
  const qs = searchParams.toString();

  // Check cache first
  const cacheKey = buildCacheKey(userId, qs);
  const cached = await getCachedJson<unknown>(cacheKey);
  if (cached) {
    return NextResponse.json(cached, { status: 200 });
  }

  // Fetch from backend
  const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
  if (sessionError || !sessionData?.session?.access_token) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }

  const url = `${getBackendApiUrl()}/api/attachments/files${qs ? `?${qs}` : ""}`;
  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${sessionData.session.access_token}` },
    method: "GET",
  });

  const data = await response.json();
  if (!response.ok) {
    return NextResponse.json(
      { error: (data as { detail?: string })?.detail || "Failed to fetch attachments" },
      { status: response.status }
    );
  }

  // Cache successful response
  await setCachedJson(cacheKey, data, CACHE_TTL_SECONDS);

  return NextResponse.json(data, { status: 200 });
});
