/**
 * @fileoverview Router agent for classifying user messages into workflows.
 *
 * Uses AI SDK v6 generateObject to classify user messages into agent workflows
 * with confidence scores and reasoning.
 *
 * Note: This agent uses generateObject directly, not ToolLoopAgent, because
 * message classification is a single-shot structured output operation - not
 * an agentic multi-step workflow.
 */

import "server-only";

import type { RouterClassification } from "@schemas/agents";
import { routerClassificationSchema } from "@schemas/agents";
import type { LanguageModel } from "ai";
import { generateObject } from "ai";
import { buildRouterPrompt } from "@/prompts/agents";

/**
 * Classify a user message into an agent workflow.
 *
 * Uses generateObject to produce structured classification with agent workflow,
 * confidence score, and optional reasoning.
 *
 * @param deps Language model for classification.
 * @param userMessage User message to classify.
 * @returns Promise resolving to router classification result.
 * @throws Error if userMessage is invalid or classification fails.
 */
export async function classifyUserMessage(
  deps: { model: LanguageModel },
  userMessage: string
): Promise<RouterClassification> {
  // Validate input
  const MaxMessageLength = 10000;
  const trimmedMessage = userMessage.trim();

  if (!trimmedMessage) {
    throw new Error("User message cannot be empty");
  }

  if (trimmedMessage.length > MaxMessageLength) {
    throw new Error(
      `User message exceeds maximum length of ${MaxMessageLength} characters (received ${trimmedMessage.length})`
    );
  }

  const systemPrompt = buildRouterPrompt();

  try {
    const result = await generateObject({
      model: deps.model,
      prompt: trimmedMessage,
      schema: routerClassificationSchema,
      system: systemPrompt,
      temperature: 0.1,
    });
    return result.object;
  } catch (error) {
    const messageSummary =
      trimmedMessage.length > 100
        ? `${trimmedMessage.slice(0, 100)}...`
        : trimmedMessage;

    const errorMessage = error instanceof Error ? error.message : String(error);
    throw new Error(
      `Failed to classify user message: ${errorMessage} (message: "${messageSummary}")`
    );
  }
}
