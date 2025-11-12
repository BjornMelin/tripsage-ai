/**
 * @fileoverview Router agent for classifying user messages into workflows.
 *
 * Uses AI SDK v6 generateObject to classify user messages into agent workflows
 * with confidence scores and reasoning.
 */

import "server-only";

import type { LanguageModel } from "ai";
import { generateObject } from "ai";
import { buildRouterPrompt } from "@/prompts/agents";
import type { RouterClassification } from "@/schemas/agents";
import { routerClassificationSchema } from "@/schemas/agents";

/**
 * Classify a user message into an agent workflow.
 *
 * Uses generateObject to produce structured classification with agent workflow,
 * confidence score, and optional reasoning.
 *
 * @param deps Language model for classification.
 * @param userMessage User message to classify.
 * @returns Promise resolving to router classification result.
 */
export async function classifyUserMessage(
  deps: { model: LanguageModel },
  userMessage: string
): Promise<RouterClassification> {
  const systemPrompt = buildRouterPrompt();
  const result = await generateObject({
    model: deps.model,
    prompt: userMessage,
    schema: routerClassificationSchema,
    system: systemPrompt,
    temperature: 0.1,
  });
  return result.object;
}
