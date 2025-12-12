/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock the botid/server module before importing the module under test
vi.mock("botid/server", () => ({
  checkBotId: vi.fn(),
}));

// Mock the logger to avoid side effects
vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: () => ({
    debug: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
  }),
}));

// Import after mocks are set up
import { checkBotId } from "botid/server";
import {
  assertHumanOrThrow,
  BOT_DETECTED_RESPONSE,
  BotDetectedError,
  type BotIdVerification,
  isBotDetectedError,
} from "@/lib/security/botid";

const mockCheckBotId = vi.mocked(checkBotId);

/**
 * Helper to create a mock BotID response with all required fields.
 */
function createMockBotIdResponse(
  overrides: Partial<{
    isBot: boolean;
    isHuman: boolean;
    isVerifiedBot: boolean;
    bypassed: boolean;
    verifiedBotName: string | undefined;
    verifiedBotCategory: string | undefined;
  }> = {}
) {
  return {
    bypassed: false,
    isBot: false,
    isHuman: true,
    isVerifiedBot: false,
    verifiedBotCategory: undefined,
    verifiedBotName: undefined,
    ...overrides,
  };
}

describe("BotDetectedError", () => {
  it("creates error with correct properties", () => {
    const verification: BotIdVerification = {
      bypassed: false,
      isBot: true,
      isHuman: false,
      isVerifiedBot: false,
      verifiedBotCategory: undefined,
      verifiedBotName: undefined,
    };

    const error = new BotDetectedError("chat.stream", verification);

    expect(error.name).toBe("BotDetectedError");
    expect(error.message).toBe("Automated access is not allowed.");
    expect(error.status).toBe(403);
    expect(error.code).toBe("bot_detected");
    expect(error.routeName).toBe("chat.stream");
    expect(error.verification).toBe(verification);
  });

  it("provides user-friendly message", () => {
    const verification: BotIdVerification = {
      bypassed: false,
      isBot: true,
      isHuman: false,
      isVerifiedBot: false,
    };
    const error = new BotDetectedError("test", verification);
    expect(error.userMessage).toBe("Automated access is not allowed.");
  });

  it("serializes to JSON without sensitive verification details", () => {
    const verification: BotIdVerification = {
      bypassed: false,
      isBot: true,
      isHuman: false,
      isVerifiedBot: false,
      verifiedBotCategory: undefined,
      verifiedBotName: undefined,
    };

    const error = new BotDetectedError("chat.stream", verification);
    const json = error.toJSON();

    expect(json).toEqual({
      code: "bot_detected",
      message: "Automated access is not allowed.",
      name: "BotDetectedError",
      routeName: "chat.stream",
      status: 403,
    });
    // Should not include verification details
    expect(json).not.toHaveProperty("verification");
  });
});

describe("isBotDetectedError", () => {
  it("returns true for BotDetectedError instances", () => {
    const verification: BotIdVerification = {
      bypassed: false,
      isBot: true,
      isHuman: false,
      isVerifiedBot: false,
    };
    const error = new BotDetectedError("test", verification);
    expect(isBotDetectedError(error)).toBe(true);
  });

  it("returns false for other Error types", () => {
    expect(isBotDetectedError(new Error("test"))).toBe(false);
    expect(isBotDetectedError(new TypeError("test"))).toBe(false);
  });

  it("returns false for non-Error values", () => {
    expect(isBotDetectedError(null)).toBe(false);
    expect(isBotDetectedError(undefined)).toBe(false);
    expect(isBotDetectedError("error")).toBe(false);
    expect(isBotDetectedError({ status: 403 })).toBe(false);
  });
});

describe("assertHumanOrThrow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not throw when checkBotId returns isBot: false", async () => {
    mockCheckBotId.mockResolvedValue(createMockBotIdResponse({ isBot: false }));

    await expect(assertHumanOrThrow("chat.stream")).resolves.toBeUndefined();
    expect(mockCheckBotId).toHaveBeenCalledWith({
      advancedOptions: { checkLevel: "basic" },
    });
  });

  it("throws BotDetectedError when bot is detected", async () => {
    mockCheckBotId.mockResolvedValue(
      createMockBotIdResponse({ isBot: true, isHuman: false })
    );

    await expect(assertHumanOrThrow("chat.stream")).rejects.toThrow(BotDetectedError);
  });

  it("throws with correct route name in error", async () => {
    mockCheckBotId.mockResolvedValue(
      createMockBotIdResponse({ isBot: true, isHuman: false })
    );

    try {
      await assertHumanOrThrow("agent.router");
      expect.fail("Should have thrown");
    } catch (error) {
      expect(isBotDetectedError(error)).toBe(true);
      expect((error as BotDetectedError).routeName).toBe("agent.router");
    }
  });

  it("allows verified AI assistants by default", async () => {
    mockCheckBotId.mockResolvedValue(
      createMockBotIdResponse({
        isBot: true,
        isHuman: false,
        isVerifiedBot: true,
        verifiedBotCategory: "ai_assistant",
        verifiedBotName: "ChatGPT",
      })
    );

    // Should not throw because allowVerifiedAiAssistants defaults to true
    await expect(assertHumanOrThrow("chat.stream")).resolves.toBeUndefined();
  });

  it("blocks verified bots that are not AI assistants", async () => {
    mockCheckBotId.mockResolvedValue(
      createMockBotIdResponse({
        isBot: true,
        isHuman: false,
        isVerifiedBot: true,
        verifiedBotCategory: "search_crawler",
        verifiedBotName: "Googlebot",
      })
    );

    await expect(assertHumanOrThrow("chat.stream")).rejects.toThrow(BotDetectedError);
  });

  it("blocks AI assistants when allowVerifiedAiAssistants is false", async () => {
    mockCheckBotId.mockResolvedValue(
      createMockBotIdResponse({
        isBot: true,
        isHuman: false,
        isVerifiedBot: true,
        verifiedBotCategory: "ai_assistant",
        verifiedBotName: "ChatGPT",
      })
    );

    await expect(
      assertHumanOrThrow("chat.stream", { allowVerifiedAiAssistants: false })
    ).rejects.toThrow(BotDetectedError);
  });

  it("propagates errors from checkBotId", async () => {
    const networkError = new Error("Network failure");
    mockCheckBotId.mockRejectedValue(networkError);

    await expect(assertHumanOrThrow("chat.stream")).rejects.toThrow(networkError);
  });

  it("allows requests when BotID is bypassed", async () => {
    mockCheckBotId.mockResolvedValue(createMockBotIdResponse({ bypassed: true }));

    await expect(assertHumanOrThrow("chat.stream")).resolves.toBeUndefined();
  });

  it("passes deep level option to checkBotId", async () => {
    mockCheckBotId.mockResolvedValue(createMockBotIdResponse({ isBot: false }));

    await assertHumanOrThrow("chat.stream", { level: "deep" });

    expect(mockCheckBotId).toHaveBeenCalledWith({
      advancedOptions: { checkLevel: "deepAnalysis" },
    });
  });

  it("uses basic level by default", async () => {
    mockCheckBotId.mockResolvedValue(createMockBotIdResponse({ isBot: false }));

    await assertHumanOrThrow("chat.stream");

    expect(mockCheckBotId).toHaveBeenCalledWith({
      advancedOptions: { checkLevel: "basic" },
    });
  });

  it("allows requests when bypassed is true (local development)", async () => {
    // In local development, BotID returns bypassed: true with isBot: false
    mockCheckBotId.mockResolvedValue(
      createMockBotIdResponse({
        bypassed: true,
        isBot: false,
        isHuman: true,
      })
    );

    await expect(assertHumanOrThrow("chat.stream")).resolves.toBeUndefined();
  });
});

describe("BOT_DETECTED_RESPONSE", () => {
  it("has correct error structure matching spec", () => {
    expect(BOT_DETECTED_RESPONSE).toEqual({
      error: "bot_detected",
      reason: "Automated access is not allowed.",
    });
  });
});
