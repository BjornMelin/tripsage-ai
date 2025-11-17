/**
 * @fileoverview Hardened Next.js route handler for streaming chat responses.
 * - SSR auth via Supabase cookies
 * - Upstash Ratelimit sliding window (40/min)
 * - Provider registry + BYOK (SSR-only)
 * - Token clamping + usage metadata via messageMetadata
 * - Attachments mapping (image-only) and basic validation
 * - Minimal structured logs with redaction (no prompt logging)
 */

import "server-only";

import type { UIMessage } from "ai";
import type { NextRequest } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { getClientIpFromHeaders } from "@/lib/next/route-helpers";
import { resolveProvider } from "@/lib/providers/registry";
import { handleChatStream } from "./_handler";

// Avoid public caching; this route depends on auth/session
export const dynamic = "force-dynamic";

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
  auth: false,
  rateLimit: "chat:stream",
  telemetry: "chat.stream",
})(async (req: NextRequest, { supabase }): Promise<Response> => {
  // Parse
  let body: IncomingBody | undefined;
  try {
    body = (await req.json()) as IncomingBody;
  } catch {
    body = { messages: [] };
  }
  const ip = getClientIpFromHeaders(req);
  return handleChatStream(
    {
      clock: { now: () => Date.now() },
      config: { defaultMaxTokens: 1024 },
      limit: undefined, // Rate limiting handled by factory
      logger: { error: console.error, info: console.info },
      resolveProvider: (userId, modelHint) => resolveProvider(userId, modelHint),
      supabase,
    },
    { ...body, ip }
  );
});
