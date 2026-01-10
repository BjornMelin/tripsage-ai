/**
 * @fileoverview Attachment files listing endpoint.
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
    (params.chatId !== undefined ? `&chatId=${params.chatId}` : "") +
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
  botId: true,
  rateLimit: "attachments:files",
  telemetry: "attachments.files.read",
})(async (req: NextRequest, { user, supabase }) => {
  const userResult = requireUserId(user);
  if (!userResult.ok) return userResult.error;
  const userId = userResult.data;

  // Parse and validate query parameters
  const { searchParams } = req.nextUrl;
  const queryResult = attachmentListQuerySchema.safeParse({
    chatId: searchParams.get("chatId") ?? undefined,
    chatMessageId: searchParams.get("chatMessageId") ?? undefined,
    limit: searchParams.get("limit") ?? undefined,
    offset: searchParams.get("offset") ?? undefined,
    tripId: searchParams.get("tripId") ?? undefined,
  });

  if (!queryResult.success) {
    return errorResponse({
      err: queryResult.error,
      error: "invalid_request",
      issues: queryResult.error.issues,
      reason: "Invalid query parameters",
      status: 400,
    });
  }

  const { chatId, tripId, chatMessageId, limit, offset } = queryResult.data;

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
    .order("created_at", { ascending: false })
    .range(offset, offset + limit - 1);

  // When listing trip-scoped attachments, rely on RLS to allow collaborators to read.
  // Default behavior (no tripId) remains owner-scoped for efficiency.
  if (tripId === undefined) {
    query = query.eq("user_id", userId);
  }

  // Filter by tripId if provided (Zod coercion ensures it's a number)
  if (tripId !== undefined) {
    query = query.eq("trip_id", tripId);
  }

  // Filter by chatId if provided
  if (chatId !== undefined) {
    query = query.eq("chat_id", chatId);
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
        const validEntries = signedData.filter(
          (s): s is { path: string; signedUrl: string; error: string | null } => {
            const hasPath = typeof s.path === "string" && s.path.trim().length > 0;
            const hasUrl =
              typeof s.signedUrl === "string" && s.signedUrl.trim().length > 0;
            const noError =
              s.error === null || s.error === undefined || s.error.length === 0;
            return hasPath && hasUrl && noError;
          }
        );

        const skipped = signedData.length - validEntries.length;
        if (skipped > 0) {
          logger.warn("Skipped signed URL entries without valid paths", {
            bucket: STORAGE_BUCKET,
            pathCount: paths.length,
            skipped,
            userId,
          });
        }

        const dedupedEntries: Array<[string, string]> = [];
        const seenPaths = new Set<string>();

        for (const entry of validEntries) {
          const path = entry.path;

          if (seenPaths.has(path)) {
            continue;
          }
          seenPaths.add(path);
          dedupedEntries.push([path, entry.signedUrl]);
        }

        urlMap = new Map(dedupedEntries);
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

  // Transform to response format, filtering out items without valid URLs
  const allItems = attachments ?? [];
  const items = allItems
    .map((att) => {
      const urlKey = typeof att.file_path === "string" ? att.file_path : null;
      const url = urlKey ? urlMap.get(urlKey) : undefined;

      // Skip items without valid signed URLs (schema requires url to be non-null)
      if (!url) {
        return null;
      }

      return {
        chatId: att.chat_id ?? null,
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
        url,
      };
    })
    .filter((item): item is NonNullable<typeof item> => item !== null);

  // Log if items were filtered due to missing URLs
  const droppedCount = allItems.length - items.length;
  if (droppedCount > 0) {
    logger.warn("Filtered attachments without valid signed URLs", {
      dropped: droppedCount,
      total: allItems.length,
      userId,
    });
  }

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
