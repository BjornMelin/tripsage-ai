/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

// Hoisted mocks per testing.md Pattern A
const mockGenerateObject = vi.hoisted(() => vi.fn());
const mockBuildRouterPrompt = vi.hoisted(() => vi.fn());

vi.mock("server-only", () => ({}));

vi.mock("ai", () => ({
  generateObject: mockGenerateObject,
}));

vi.mock("@/prompts/agents", () => ({
  buildRouterPrompt: mockBuildRouterPrompt,
}));

import { classifyUserMessage } from "../router-agent";

describe("classifyUserMessage", () => {
  const mockModel = { modelId: "test-model" } as Parameters<
    typeof classifyUserMessage
  >[0]["model"];

  beforeEach(() => {
    vi.clearAllMocks();
    mockBuildRouterPrompt.mockReturnValue("System prompt for routing");
    mockGenerateObject.mockResolvedValue({
      object: {
        confidence: 0.95,
        reasoning: "User is asking about flights",
        workflow: "flights",
      },
    });
  });

  it("classifies user message successfully", async () => {
    const result = await classifyUserMessage(
      { model: mockModel },
      "Find me flights from NYC to LA"
    );

    expect(result).toEqual({
      confidence: 0.95,
      reasoning: "User is asking about flights",
      workflow: "flights",
    });
    expect(mockGenerateObject).toHaveBeenCalledWith({
      model: mockModel,
      prompt: "Find me flights from NYC to LA",
      schema: expect.anything(),
      system: "System prompt for routing",
      temperature: 0.1,
    });
  });

  it("throws error for empty message", async () => {
    await expect(classifyUserMessage({ model: mockModel }, "")).rejects.toThrow(
      "User message cannot be empty"
    );
    expect(mockGenerateObject).not.toHaveBeenCalled();
  });

  it("throws error for whitespace-only message", async () => {
    await expect(
      classifyUserMessage({ model: mockModel }, "   \t\n  ")
    ).rejects.toThrow("User message cannot be empty");
    expect(mockGenerateObject).not.toHaveBeenCalled();
  });

  it("throws error for message exceeding max length", async () => {
    const longMessage = "a".repeat(10001);

    await expect(
      classifyUserMessage({ model: mockModel }, longMessage)
    ).rejects.toThrow(/exceeds maximum length/);
    expect(mockGenerateObject).not.toHaveBeenCalled();
  });

  it("trims message before processing", async () => {
    await classifyUserMessage({ model: mockModel }, "  hello world  ");

    expect(mockGenerateObject).toHaveBeenCalledWith(
      expect.objectContaining({
        prompt: "hello world",
      })
    );
  });

  it("wraps generateObject errors with context", async () => {
    mockGenerateObject.mockRejectedValue(new Error("API timeout"));

    await expect(
      classifyUserMessage({ model: mockModel }, "test message")
    ).rejects.toThrow("Failed to classify user message: API timeout");
  });

  it("handles non-Error throws", async () => {
    mockGenerateObject.mockRejectedValue("string error");

    await expect(
      classifyUserMessage({ model: mockModel }, "test message")
    ).rejects.toThrow("Failed to classify user message: string error");
  });
});
