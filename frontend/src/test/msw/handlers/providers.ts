/**
 * @fileoverview MSW handlers for AI provider endpoints.
 *
 * Provides default mock responses for AI provider integrations.
 */

import { HttpResponse, http } from "msw";

/**
 * Default AI provider handlers providing happy-path responses.
 *
 * Note: These are placeholder handlers. Actual AI SDK streaming
 * should be mocked using official AI SDK test utilities (MockLanguageModelV3).
 */
export const providersHandlers = [
  // OpenAI API mock (for direct API calls, not AI SDK)
  http.post("https://api.openai.com/v1/chat/completions", () => {
    return HttpResponse.json({
      choices: [
        {
          // biome-ignore lint/style/useNamingConvention: match OpenAI payload shape
          finish_reason: "stop",
          index: 0,
          message: {
            content: "This is a mock OpenAI response",
            role: "assistant",
          },
        },
      ],
      created: Date.now(),
      id: "chatcmpl-mock",
      model: "gpt-4o-mini",
      object: "chat.completion",
      usage: {
        // biome-ignore lint/style/useNamingConvention: match OpenAI payload shape
        completion_tokens: 20,
        // biome-ignore lint/style/useNamingConvention: match OpenAI payload shape
        prompt_tokens: 10,
        // biome-ignore lint/style/useNamingConvention: match OpenAI payload shape
        total_tokens: 30,
      },
    });
  }),

  // Anthropic API mock (for direct API calls, not AI SDK)
  http.post("https://api.anthropic.com/v1/messages", () => {
    return HttpResponse.json({
      content: [
        {
          text: "This is a mock Anthropic response",
          type: "text",
        },
      ],
      id: "msg-mock",
      model: "claude-3-5-sonnet-20241022",
      role: "assistant",
      // biome-ignore lint/style/useNamingConvention: match Anthropic payload shape
      stop_reason: "end_turn",
      type: "message",
      usage: {
        // biome-ignore lint/style/useNamingConvention: match Anthropic payload shape
        input_tokens: 10,
        // biome-ignore lint/style/useNamingConvention: match Anthropic payload shape
        output_tokens: 20,
      },
    });
  }),
];
