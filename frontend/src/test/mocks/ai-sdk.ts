/**
 * @fileoverview AI SDK mocks for tests.
 * Use this in tests that import AI SDK modules.
 */

import { vi } from "vitest";

/**
 * Sets up AI SDK mocks for a test file.
 * Call this at the top level of test files that use AI SDK.
 *
 * @example
 * ```ts
 * import { setupAISDKMocks } from "@/test/mocks/ai-sdk";
 * setupAISDKMocks();
 * ```
 */
export function setupAISDKMocks() {
  // Mock AI SDK core
  vi.mock("ai", () => ({
    convertToModelMessages: vi.fn((messages) => messages),
    generateObject: vi.fn(() => Promise.resolve({ object: {} })),
    Output: {
      object: vi.fn(() => ({ schema: {} })),
    },
    openai: vi.fn(() => ({ model: "gpt-4o-mini" })),
    streamObject: vi.fn(() => ({
      toUIMessageStreamResponse: vi.fn(() => new Response()),
    })),
    streamText: vi.fn(() => ({
      toUIMessageStreamResponse: vi.fn(() => new Response()),
    })),
    tool: vi.fn((config) => config),
  }));

  // Mock AI SDK React hooks
  vi.mock("@ai-sdk/react", () => ({
    useChat: vi.fn(() => ({
      error: null,
      handleInputChange: vi.fn(),
      handleSubmit: vi.fn(),
      input: "",
      isLoading: false,
      messages: [],
    })),
    useCompletion: vi.fn(() => ({
      completion: "",
      error: null,
      handleInputChange: vi.fn(),
      handleSubmit: vi.fn(),
      input: "",
      isLoading: false,
    })),
  }));
}
