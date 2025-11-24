/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { unstubAllEnvs } from "@/test/env-helpers";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/route-helpers";

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

const mockGetUser = vi.fn();
const mockFrom = vi.fn();
const mockResolveProvider = vi.fn();
const mockGenerateText = vi.fn();

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: { getUser: mockGetUser },
    from: mockFrom,
  })),
}));

vi.mock("@ai/models/registry", () => ({
  resolveProvider: mockResolveProvider,
}));

vi.mock("ai", () => ({
  convertToModelMessages: (x: unknown) => x,
  generateText: mockGenerateText,
}));

vi.mock("@upstash/ratelimit", () => ({
  Ratelimit: vi.fn(() => ({
    limit: vi.fn().mockResolvedValue({
      limit: 40,
      remaining: 39,
      reset: Date.now() + 60000,
      success: true,
    }),
  })),
  slidingWindow: vi.fn(),
}));

vi.mock("@upstash/redis", () => ({
  Redis: {
    fromEnv: vi.fn(() => ({})),
  },
}));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVarWithFallback: vi.fn(() => undefined),
}));

// Mock route helpers
vi.mock("@/lib/api/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/route-helpers")>(
    "@/lib/api/route-helpers"
  );
  return {
    ...actual,
    getClientIpFromHeaders: vi.fn(() => "127.0.0.1"),
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});

describe("/api/chat route smoke", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    unstubAllEnvs();
    mockGetUser.mockReset();
    mockFrom.mockReset();
    mockResolveProvider.mockReset();
    mockGenerateText.mockReset();
  });

  it("returns 401 unauthenticated", async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } });
    const mod = await import("../route");
    const req = createMockNextRequest({
      body: { messages: [] },
      method: "POST",
      url: "http://localhost/api/chat",
    });
    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(401);
  });

  it("returns 200 on success", async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: "u1" } } });
    mockFrom.mockReturnValue({
      insert: vi.fn(async () => ({ error: null })),
    });
    mockResolveProvider.mockResolvedValue({
      model: {},
      modelId: "gpt-4o-mini",
      provider: "openai",
    });
    mockGenerateText.mockResolvedValue({
      text: "ok",
      usage: { inputTokens: 1, outputTokens: 2, totalTokens: 3 },
    });
    const mod = await import("../route");
    const req = createMockNextRequest({
      body: { messages: [] },
      method: "POST",
      url: "http://localhost/api/chat",
    });
    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.content).toBe("ok");
    expect(body.model).toBe("gpt-4o-mini");
  });
});
