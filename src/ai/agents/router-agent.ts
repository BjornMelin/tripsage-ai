/**
 * @fileoverview Router agent for classifying user messages into workflows.
 */

import "server-only";

import { buildTimeoutConfig, DEFAULT_AI_TIMEOUT_MS } from "@ai/timeout";
import type { RouterClassification } from "@schemas/agents";
import { routerClassificationSchema } from "@schemas/agents";
import type { LanguageModel } from "ai";
import { generateText, Output } from "ai";
import { sanitizeWithInjectionDetection } from "@/lib/security/prompt-sanitizer";
import { buildRouterPrompt } from "@/prompts/agents";

const MAX_MESSAGE_LENGTH = 10_000;

/**
 * Router agent dependencies.
 */
export interface RouterAgentDeps {
  /** Language model for classification. */
  model: LanguageModel;
  /** Optional identifier for internal diagnostics (NOT sent to AI provider telemetry). */
  identifier?: string;
  /** Optional model ID for telemetry. */
  modelId?: string;
  /** Optional abort signal for request cancellation. */
  abortSignal?: AbortSignal;
}

export class InvalidPatternsError extends Error {
  readonly code = "invalid_patterns";

  constructor(
    message = "User message contains only invalid patterns and cannot be processed"
  ) {
    super(message);
    this.name = "InvalidPatternsError";
  }
}

/**
 * Classify a user message into an agent workflow.
 *
 * Uses AI SDK v6 generateText with Output.object() for structured output.
 * This is the v6 unified API that replaces deprecated generateObject().
 *
 * @param deps Language model and optional telemetry identifiers.
 * @param userMessage User message to classify.
 * @returns Promise resolving to router classification result.
 * @throws Error if userMessage is invalid or classification fails.
 */
export async function classifyUserMessage(
  deps: RouterAgentDeps,
  userMessage: string
): Promise<RouterClassification> {
  // Validate input
  const trimmedMessage = userMessage.trim();

  if (!trimmedMessage) {
    throw new Error("User message cannot be empty");
  }

  if (trimmedMessage.length > MAX_MESSAGE_LENGTH) {
    throw new Error(
      `User message exceeds maximum length of ${MAX_MESSAGE_LENGTH} characters (received ${trimmedMessage.length})`
    );
  }

  // Sanitize message to prevent prompt injection attacks
  const sanitizedMessage = sanitizeWithInjectionDetection(
    trimmedMessage,
    MAX_MESSAGE_LENGTH
  );

  if (!sanitizedMessage.trim()) {
    throw new InvalidPatternsError();
  }
  const systemPrompt = buildRouterPrompt();

  try {
    const result = await generateText({
      abortSignal: deps.abortSignal,
      // biome-ignore lint/style/useNamingConvention: AI SDK API uses snake_case
      experimental_telemetry: {
        functionId: "router.classifyUserMessage",
        isEnabled: true,
        metadata: {
          ...(deps.modelId ? { modelId: deps.modelId } : {}),
        },
      },
      model: deps.model,
      // Output.object() is the v6 unified API for structured output
      output: Output.object({
        schema: routerClassificationSchema,
      }),
      prompt: sanitizedMessage,
      system: systemPrompt,
      // Low temperature for consistent classification
      temperature: 0.1,
      timeout: buildTimeoutConfig(DEFAULT_AI_TIMEOUT_MS),
    });
    if (!result.output) {
      throw new Error("Router classification missing structured output from model");
    }

    return result.output as RouterClassification;
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    throw new Error(`Failed to classify user message: ${errorMessage}`, {
      cause: error instanceof Error ? error : undefined,
    });
  }
}
