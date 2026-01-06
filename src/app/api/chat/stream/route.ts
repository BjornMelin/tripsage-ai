/**
 * @fileoverview Hardened Next.js route handler for streaming chat responses.
 */

import "server-only";

import { resolveProvider } from "@ai/models/registry";
import { safeValidateUIMessages } from "ai";
import type { NextRequest } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import {
  errorResponse,
  getClientIpFromHeaders,
  parseJsonBody,
  requireUserId,
} from "@/lib/api/route-helpers";
import { createServerLogger } from "@/lib/telemetry/logger";
import { handleChatStream } from "./_handler";

// Allow streaming responses for up to 60 seconds
export const maxDuration = 60;

const chatStreamRequestSchema = z.looseObject({
  desiredMaxTokens: z.coerce.number().int().min(1).max(16_384).optional(),
  messages: z.unknown().optional(),
  model: z.string().trim().min(1).max(200).optional(),
  sessionId: z.string().trim().min(1).max(200).optional(),
});

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
  if (!auth.ok) return auth.error;
  const userId = auth.data;

  const parsed = await parseJsonBody(req);
  if (!parsed.ok) return parsed.error;

  const requestValidation = chatStreamRequestSchema.safeParse(parsed.data);
  if (!requestValidation.success) {
    return errorResponse({
      err: requestValidation.error,
      error: "invalid_request",
      issues: requestValidation.error.issues,
      reason: "Request validation failed",
      status: 400,
    });
  }

  const body = requestValidation.data;

  const rawMessages = body.messages;
  if (rawMessages !== undefined && !Array.isArray(rawMessages)) {
    return errorResponse({
      error: "invalid_request",
      reason: "messages must be an array",
      status: 400,
    });
  }

  const rawMessagesArray = Array.isArray(rawMessages) ? rawMessages : [];
  const safeMessagesResult =
    rawMessagesArray.length > 0
      ? await safeValidateUIMessages({ messages: rawMessagesArray })
      : { data: [], success: true as const };
  if (!safeMessagesResult.success) {
    return errorResponse({
      err: safeMessagesResult.error,
      error: "invalid_request",
      reason: "Invalid messages payload",
      status: 400,
    });
  }

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
    {
      abortSignal: req.signal,
      desiredMaxTokens: body.desiredMaxTokens,
      ip,
      messages: safeMessagesResult.data,
      model: body.model,
      sessionId: body.sessionId,
      userId,
    }
  );
});
