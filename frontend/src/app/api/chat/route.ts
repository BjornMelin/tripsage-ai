/**
 * @fileoverview Next.js Route Handler for non-streaming chat responses.
 * Thin adapter: SSR auth via Supabase, provider resolution, token clamping
 * through DI handler, and safe JSON response with usage metadata.
 */

import "server-only";

import { resolveProvider } from "@ai/models/registry";
import type { UIMessage } from "ai";
import type { NextRequest } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { getClientIpFromHeaders, parseJsonBody } from "@/lib/api/route-helpers";
import { createServerLogger } from "@/lib/telemetry/logger";
import { handleChatNonStream } from "./_handler";

// Allow up to 30s for non-stream completion
export const maxDuration = 30;

/**
 * Type representing the incoming body for the chat route.
 *
 * @param messages - The messages.
 * @param session_id - The session ID.
 * @param model - The model.
 * @param desiredMaxTokens - The desired maximum tokens.
 */
type IncomingBody = {
  messages?: UIMessage[];
  sessionId?: string;
  model?: string;
  desiredMaxTokens?: number;
};

/**
 * Handles POST requests for chat responses.
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
