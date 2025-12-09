/**
 * @fileoverview Non-streaming chat send route.
 * Route: POST /api/chat/send
 *
 * Provides a dedicated endpoint for non-streaming chat messages.
 * Delegates to the existing /api/chat handler implementation.
 */

import "server-only";

import { resolveProvider } from "@ai/models/registry";
import { chatNonStreamRequestSchema } from "@schemas/chat";
import type { UIMessage } from "ai";
import type { NextRequest } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import {
  getClientIpFromHeaders,
  parseJsonBody,
  validateSchema,
} from "@/lib/api/route-helpers";
import { createServerLogger } from "@/lib/telemetry/logger";
import { handleChatNonStream } from "../_handler";

// Allow up to 30s for non-stream completion
export const maxDuration = 30;

/**
 * Handle POST /api/chat/send to send a non-streaming chat message.
 *
 * @param req - The Next.js request object.
 * @param routeContext - Route context from withApiGuards
 * @returns Promise resolving to a Response with chat completion data.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "chat:nonstream",
  telemetry: "chat.nonstream",
})(async (req: NextRequest, { supabase }): Promise<Response> => {
  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }

  const validation = validateSchema(chatNonStreamRequestSchema, parsed.body);
  if ("error" in validation) {
    return validation.error;
  }
  const validatedBody = validation.data;

  // Type assertion for messages array - validated structure, handler validates UIMessage format
  const body = {
    ...validatedBody,
    messages: validatedBody.messages as UIMessage[] | undefined,
  };

  const ip = getClientIpFromHeaders(req);
  const logger = createServerLogger("chat.nonstream");

  return await handleChatNonStream(
    {
      clock: { now: () => Date.now() },
      config: { defaultMaxTokens: 1024 },
      limit: undefined, // Rate limiting handled by factory
      logger,
      resolveProvider: (userId, modelHint) => resolveProvider(userId, modelHint),
      supabase,
    },
    { ...body, ip }
  );
});
