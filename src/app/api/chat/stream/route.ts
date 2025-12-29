/**
 * @fileoverview Hardened Next.js route handler for streaming chat responses.
 */

import "server-only";

import { resolveProvider } from "@ai/models/registry";
import type { UIMessage } from "ai";
import type { NextRequest } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import {
  getClientIpFromHeaders,
  parseJsonBody,
  requireUserId,
} from "@/lib/api/route-helpers";
import { createServerLogger } from "@/lib/telemetry/logger";
import { handleChatStream } from "./_handler";

// Allow streaming responses for up to 60 seconds
export const maxDuration = 60;

/**
 * Type definition for the incoming request body structure.
 */
type IncomingBody = {
  messages?: UIMessage[];
  sessionId?: string;
  model?: string;
  desiredMaxTokens?: number;
};

/**
 * Handles POST requests for streaming chat responses with AI SDK.
 *
 * Performs authentication, rate limiting, provider resolution, token budgeting,
 * memory integration, and streams AI responses with comprehensive error handling
 * and usage metadata.
 *
 * @param req - The Next.js request object.
 * @param routeContext - Route context from withApiGuards
 * @returns Promise resolving to a Response with streamed chat data.
 */
export const POST = withApiGuards({
  auth: true,
  botId: true,
  rateLimit: "chat:stream",
  telemetry: "chat.stream",
})(async (req: NextRequest, { supabase, user }): Promise<Response> => {
  const auth = requireUserId(user);
  if ("error" in auth) {
    return auth.error;
  }

  // Parse with fallback to empty messages
  const parsed = await parseJsonBody(req);
  const body: IncomingBody =
    "error" in parsed ? { messages: [] } : (parsed.body as IncomingBody);
  const ip = getClientIpFromHeaders(req);
  const logger = createServerLogger("chat.stream");
  return handleChatStream(
    {
      clock: { now: () => Date.now() },
      config: { defaultMaxTokens: 1024 },
      logger,
      resolveProvider: (userId, modelHint) => resolveProvider(userId, modelHint),
      supabase,
    },
    { ...body, abortSignal: req.signal, ip, userId: auth.userId }
  );
});
