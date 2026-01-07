/**
 * @fileoverview Canonical streaming chat route (AI SDK v6 UI stream protocol).
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
import { handleChat } from "./_handler";

// Allow streaming responses for up to 60 seconds.
export const maxDuration = 60;

const DEFAULT_MAX_TOKENS_FALLBACK = 1024;
const DEFAULT_MAX_STEPS_FALLBACK = 10;

function getDefaultMaxTokens(): number {
  const raw = process.env.CHAT_DEFAULT_MAX_TOKENS;
  const parsed = raw ? Number.parseInt(raw, 10) : Number.NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_MAX_TOKENS_FALLBACK;
}

function getDefaultMaxSteps(): number {
  const raw = process.env.CHAT_DEFAULT_MAX_STEPS;
  const parsed = raw ? Number.parseInt(raw, 10) : Number.NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_MAX_STEPS_FALLBACK;
}

const chatRequestSchema = z.looseObject({
  desiredMaxTokens: z.number().int().min(1).max(16_384).optional(),
  id: z.string().trim().min(1).max(200).optional(),
  message: z.unknown().optional(),
  messageId: z.string().trim().min(1).max(200).optional(),
  messages: z.unknown().optional(),
  model: z.string().trim().min(1).max(200).optional(),
  sessionId: z.string().trim().min(1).max(200).optional(),
  trigger: z.enum(["submit-message", "regenerate-message"]).optional(),
});

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

  const requestValidation = chatRequestSchema.safeParse(parsed.data);
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
  const rawMessage = body.message;

  if (rawMessages !== undefined && !Array.isArray(rawMessages)) {
    return errorResponse({
      error: "invalid_request",
      reason: "messages must be an array",
      status: 400,
    });
  }

  const rawMessagesArray: unknown[] =
    rawMessage !== undefined
      ? [rawMessage]
      : Array.isArray(rawMessages)
        ? rawMessages
        : [];
  const safeMessagesResult =
    rawMessagesArray.length === 0
      ? { data: [], success: true as const }
      : await safeValidateUIMessages({ messages: rawMessagesArray });
  if (!safeMessagesResult.success) {
    const normalizedError =
      safeMessagesResult.error instanceof Error
        ? safeMessagesResult.error
        : new Error(String(safeMessagesResult.error ?? "Invalid messages payload"));
    return errorResponse({
      err: normalizedError,
      error: "invalid_request",
      reason: "Invalid messages payload",
      status: 400,
    });
  }

  // Prevent client-side injection of system messages; system prompts are server-controlled.
  if (safeMessagesResult.data.some((message) => message.role === "system")) {
    return errorResponse({
      error: "invalid_request",
      reason: "system messages are not allowed",
      status: 400,
    });
  }

  const ip = getClientIpFromHeaders(req);
  const logger = createServerLogger("chat");
  const defaultMaxTokens = getDefaultMaxTokens();
  const maxSteps = getDefaultMaxSteps();
  return handleChat(
    {
      clock: { now: () => Date.now() },
      config: { defaultMaxTokens, maxSteps },
      logger,
      resolveProvider: (resolvedUserId, modelHint) =>
        resolveProvider(resolvedUserId, modelHint),
      supabase,
    },
    {
      abortSignal: req.signal,
      desiredMaxTokens: body.desiredMaxTokens,
      ip,
      messageId: body.messageId,
      messages: safeMessagesResult.data,
      model: body.model,
      sessionId: body.sessionId,
      trigger: body.trigger,
      userId,
    }
  );
});
