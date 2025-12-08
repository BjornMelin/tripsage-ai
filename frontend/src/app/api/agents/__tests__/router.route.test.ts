/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createRouteParamsContext,
  makeJsonRequest,
  mockApiRouteAuthUser,
  resetApiRouteMocks,
} from "@/test/helpers/api-route";

const classifyUserMessage = vi.hoisted(() => vi.fn());

vi.mock("@ai/agents/router-agent", () => ({
  classifyUserMessage,
  InvalidPatternsError: class InvalidPatternsError extends Error {
    constructor(message?: string) {
      super(message ?? "invalid patterns");
      this.name = "InvalidPatternsError";
      // @ts-expect-error test shim
      this.code = "invalid_patterns";
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
});
