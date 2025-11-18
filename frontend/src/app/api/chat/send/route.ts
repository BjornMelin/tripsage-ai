/**
 * @fileoverview Non-streaming chat send route.
 * Route: POST /api/chat/send
 *
 * Provides a dedicated endpoint for non-streaming chat messages.
 * Delegates to the existing /api/chat handler implementation.
 */

import "server-only";

import type { UIMessage } from "ai";
import type { NextRequest } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { createServerLogger } from "@/lib/logging/server";
import { getClientIpFromHeaders, parseJsonBody } from "@/lib/next/route-helpers";
import { resolveProvider } from "@/lib/providers/registry";
import { handleChatNonStream } from "../_handler";

// Allow up to 30s for non-stream completion
export const maxDuration = 30;

/**
 * Type representing the incoming body for the chat send route.
 */
type IncomingBody = {
  messages?: UIMessage[];
  sessionId?: string;
  model?: string;
  desiredMaxTokens?: number;
};

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
    return new Response(JSON.stringify({ error: "Malformed JSON in request body." }), {
      headers: { "Content-Type": "application/json" },
      status: 400,
    });
  }
  const body = parsed.body as IncomingBody;

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
    { ...(body || {}), ip }
  );
});
