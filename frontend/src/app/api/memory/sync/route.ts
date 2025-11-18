/**
 * @fileoverview Memory sync API route.
 * Route: POST /api/memory/sync
 *
 * Handles memory sync requests from client stores and enqueues QStash jobs.
 * Security: Prevent caching of user-specific memory sync data per ADR-0024.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { parseJsonBody, validateSchema } from "@/lib/next/route-helpers";
import {
  enqueueConversationMemorySync,
  enqueueFullMemorySync,
  enqueueIncrementalMemorySync,
} from "@/lib/qstash/memory-sync";

/**
 * Schema for conversation memory sync request.
 */
const conversationSyncSchema = z.strictObject({
  messages: z.array(
    z.strictObject({
      content: z.string(),
      metadata: z.record(z.string(), z.unknown()).optional(),
      role: z.enum(["user", "assistant", "system"]),
      timestamp: z.string(),
    })
  ),
  mode: z.literal("conversation"),
  sessionId: z.string(),
  userId: z.string(),
});

/**
 * Schema for full memory sync request.
 */
const fullSyncSchema = z.strictObject({
  mode: z.literal("full"),
  sessionId: z.string(),
  userId: z.string(),
});

/**
 * Schema for incremental memory sync request.
 */
const incrementalSyncSchema = z.strictObject({
  mode: z.literal("incremental"),
  sessionId: z.string(),
  userId: z.string(),
});

/**
 * Discriminated union schema for memory sync requests.
 */
const memorySyncRequestSchema = z.discriminatedUnion("mode", [
  conversationSyncSchema,
  fullSyncSchema,
  incrementalSyncSchema,
]);

/**
 * Handle POST /api/memory/sync to enqueue memory sync jobs.
 *
 * @param req Next.js request containing JSON body with sync mode and parameters.
 * @param routeContext Route context from withApiGuards
 * @returns 200 OK with { status: "queued" } on success; 400/401/500 on error.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "memory:sync",
  telemetry: "memory.sync",
})(async (req: NextRequest, { user }): Promise<Response> => {
  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return NextResponse.json(
      { code: "BAD_REQUEST", error: "Malformed JSON in request body" },
      { status: 400 }
    );
  }

  const validation = validateSchema(memorySyncRequestSchema, parsed.body);
  if ("error" in validation) {
    return validation.error;
  }

  const body = validation.data;
  const userObj = user as { id: string } | null;

  // Ensure userId matches authenticated user
  if (!userObj || userObj.id !== body.userId) {
    return NextResponse.json(
      { code: "UNAUTHORIZED", error: "User ID mismatch" },
      { status: 401 }
    );
  }

  try {
    let result: { messageId: string; idempotencyKey: string };

    switch (body.mode) {
      case "conversation":
        result = await enqueueConversationMemorySync(
          body.sessionId,
          body.userId,
          body.messages
        );
        break;
      case "full":
        result = await enqueueFullMemorySync(body.sessionId, body.userId);
        break;
      case "incremental":
        result = await enqueueIncrementalMemorySync(body.sessionId, body.userId);
        break;
    }

    return NextResponse.json(
      {
        idempotencyKey: result.idempotencyKey,
        messageId: result.messageId,
        status: "queued",
      },
      { status: 200 }
    );
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to enqueue memory sync";
    return NextResponse.json(
      { code: "INTERNAL_ERROR", error: message },
      { status: 500 }
    );
  }
});
