/**
 * @fileoverview Attachment files listing endpoint.
 *
 * Queries Supabase directly for attachment metadata with per-user Redis caching.
 * Generates signed URLs for private storage access. See ADR-0058 and SPEC-0036.
 */

import "server-only";

import type { AttachmentListQuery } from "@schemas/attachments";
import { attachmentListQuerySchema } from "@schemas/attachments";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, requireUserId } from "@/lib/api/route-helpers";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import { createServerLogger } from "@/lib/telemetry/logger";

/** Cache TTL for attachment listings (2 minutes). */
const CACHE_TTL_SECONDS = 120;

/** Storage bucket name for attachments. */
const STORAGE_BUCKET = "attachments";

/** Signed URL expiration in seconds (1 hour). */
const SIGNED_URL_EXPIRATION = 3600;

/** Logger for attachments file listing operations. */
const logger = createServerLogger("attachments.files");

/**
 * Builds normalized cache key for attachment file listings.
 *
 * Uses sorted parameter names to ensure cache hits regardless of
 * query string ordering (e.g., ?limit=20&offset=0 vs ?offset=0&limit=20).
 *
 * @param userId - Authenticated user ID.
 * @param params - Validated query parameters.
 * @returns Redis cache key with normalized parameters.
 */
function buildCacheKey(userId: string, params: AttachmentListQuery): string {
  const normalized =
    `limit=${params.limit}&offset=${params.offset}` +
    (params.tripId !== undefined ? `&tripId=${params.tripId}` : "") +
    (params.chatMessageId !== undefined
      ? `&chatMessageId=${params.chatMessageId}`
      : "");
  return `attachments:files:${userId}:${normalized}`;
}

/**
 * GET /api/attachments/files
 *
 * Lists user attachment files with pagination support.
 * Response cached per-user in Redis with 2-minute TTL.
 * URLs are signed for secure private bucket access.
 *
 * @param req - Request with optional pagination query params.
 * @returns JSON array of attachment metadata or error.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "attachments:files",
  telemetry: "attachments.files.read",
})(async (req: NextRequest, { user, supabase }) => {
  const userResult = requireUserId(user);
  if ("error" in userResult) {
    return userResult.error;
  }
  const { userId } = userResult;

  // Parse and validate query parameters
  const { searchParams } = req.nextUrl;
  const queryResult = attachmentListQuerySchema.safeParse({
    chatMessageId: searchParams.get("chatMessageId") ?? undefined,
    limit: searchParams.get("limit") ?? undefined,
    offset: searchParams.get("offset") ?? undefined,
    tripId: searchParams.get("tripId") ?? undefined,
  });

  if (!queryResult.success) {
    return errorResponse({
      error: "invalid_request",
      reason: "Invalid query parameters",
      status: 400,
    });
  }

  const { tripId, chatMessageId, limit, offset } = queryResult.data;

  // Check cache first (with normalized key)
  const cacheKey = buildCacheKey(userId, queryResult.data);
  const cached = await getCachedJson<unknown>(cacheKey);
  if (cached) {
    return NextResponse.json(cached, { status: 200 });
  }

  // Build Supabase query - Zod already coerces to numbers
  let query = supabase
    .from("file_attachments")
    .select("*", { count: "exact" })
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
    .range(offset, offset + limit - 1);

  // Filter by tripId if provided (Zod coercion ensures it's a number)
  if (tripId !== undefined) {
    query = query.eq("trip_id", tripId);
  }

  // Filter by chatMessageId if provided (Zod coercion ensures it's a number)
  if (chatMessageId !== undefined) {
    query = query.eq("chat_message_id", chatMessageId);
  }

  const { data: attachments, error: queryError, count } = await query;

  if (queryError) {
    return errorResponse({
      err: new Error(queryError.message),
      error: "internal",
      reason: "Failed to fetch attachments",
      status: 500,
    });
  }

  const total = count ?? 0;
  const hasMore = offset + limit < total;
  const nextOffset = hasMore ? offset + limit : null;

  // Generate signed URLs for all file paths in a batch
  const paths = (attachments ?? [])
    .map((att) => att.file_path)
    .filter((path): path is string => typeof path === "string" && path.length > 0);

  let urlMap = new Map<string, string>();

  if (paths.length > 0) {
    try {
      const { data: signedData, error: signedError } = await supabase.storage
        .from(STORAGE_BUCKET)
        .createSignedUrls(paths, SIGNED_URL_EXPIRATION, { download: true });

      if (signedError) {
        logger.error("Failed to generate signed URLs", {
          bucket: STORAGE_BUCKET,
          error: signedError.message,
          pathCount: paths.length,
          userId,
        });
      } else if (signedData) {
        urlMap = new Map(signedData.map((s) => [s.path ?? "", s.signedUrl]));
      }
    } catch (error) {
      logger.error("Unexpected error generating signed URLs", {
        bucket: STORAGE_BUCKET,
        error: error instanceof Error ? error.message : String(error),
        pathCount: paths.length,
        userId,
      });
    }
  }

  // Transform to response format
  const items = (attachments ?? []).map((att) => ({
    // Keep numbers as numbers - no .toString() conversion (fixes type mismatch)
    chatMessageId: att.chat_message_id ?? null,
    createdAt: att.created_at,
    id: att.id,
    mimeType: att.mime_type,
    name: att.filename,
    originalName: att.original_filename,
    size: att.file_size,
    tripId: att.trip_id ?? null,
    updatedAt: att.updated_at,
    uploadStatus: att.upload_status,
    url: urlMap.get(att.file_path) ?? null,
  }));

  const response = {
    items,
    pagination: {
      hasMore,
      limit,
      nextOffset,
      offset,
      total,
    },
  };

  // Cache successful response
  await setCachedJson(cacheKey, response, CACHE_TTL_SECONDS);

  return NextResponse.json(response, { status: 200 });
});
