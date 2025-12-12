/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createRouteParamsContext,
  makeJsonRequest,
  mockApiRouteAuthUser,
  resetApiRouteMocks,
} from "@/test/helpers/api-route";

// Silence BotID dev warnings by stubbing to deterministic "human".
vi.mock("botid/server", () => ({
  checkBotId: vi.fn(async () => ({
    bypassed: true,
    isBot: false,
    isHuman: true,
    isVerifiedBot: false,
  })),
}));

const classifyUserMessage = vi.hoisted(() => vi.fn());

vi.mock("@ai/agents/router-agent", () => ({
  classifyUserMessage,
  InvalidPatternsError: class InvalidPatternsError extends Error {
    readonly code = "invalid_patterns";

    constructor(message?: string) {
      super(message ?? "invalid patterns");
      this.name = "InvalidPatternsError";
    }
  },
}));

vi.mock("@ai/models/registry", () => ({
  resolveProvider: vi.fn().mockResolvedValue({ model: {} }),
}));

describe("POST /api/agents/router", () => {
  beforeEach(() => {
    resetApiRouteMocks();
    classifyUserMessage.mockReset();
    mockApiRouteAuthUser({ id: "user-123" });
  });

  it("returns 400 when the sanitized message is empty/invalid", async () => {
    classifyUserMessage.mockRejectedValueOnce({
      code: "invalid_patterns",
      message: "User message contains only invalid patterns and cannot be processed",
    });

    const { POST } = await import("../router/route");
    const res = await POST(
      makeJsonRequest("http://localhost/api/agents/router", { message: "   " }),
      createRouteParamsContext()
    );

    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toBe("invalid_message");
    expect(body.reason).toContain("invalid patterns");
  });

  it("returns 400 when classifyUserMessage throws InvalidPatternsError", async () => {
    const { InvalidPatternsError } = await import("@ai/agents/router-agent");
    classifyUserMessage.mockRejectedValueOnce(
      new InvalidPatternsError("patterns removed")
    );

    const { POST } = await import("../router/route");
    const res = await POST(
      makeJsonRequest("http://localhost/api/agents/router", { message: "noop" }),
      createRouteParamsContext()
    );

    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toBe("invalid_message");
    expect(body.reason).toContain("invalid patterns");
  });
});
