/**
 * @fileoverview Cache invalidation webhook handler for database changes.
 *
 * Uses the shared webhook handler abstraction and cache registry.
 * Adds idempotency to prevent unnecessary cache version bumps.
 */

import "server-only";

import { getTagsForTable } from "@/lib/cache/registry";
import { bumpTags } from "@/lib/cache/tags";
import { createWebhookHandler } from "@/lib/webhooks/handler";

/**
 * Handles database change webhooks to invalidate related cache tags.
 *
 * Features (via handler abstraction):
 * - Rate limiting (100 req/min per IP)
 * - Body size validation (64KB max)
 * - HMAC signature verification
 * - Idempotency via Redis (prevents duplicate cache bumps)
 */
export const POST = createWebhookHandler({
  enableIdempotency: true,

  async handle(payload, _eventKey, span) {
    // Get tags from centralized registry
    const tags = getTagsForTable(payload.table);
    span.setAttribute("cache.tags", tags.join(","));
    span.setAttribute("cache.tags_count", tags.length);

    // Bump version counters for all affected tags
    const bumped = await bumpTags(tags);

    return { bumped, tags };
  },
  idempotencyTTL: 60, // Shorter TTL for cache ops
  name: "cache",
});
