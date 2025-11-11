/** @vitest-environment node */

import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { stubRateLimitDisabled, unstubAllEnvs } from "@/test/env-helpers";

const mockCreateOpenAI = vi.fn();
const mockCreateAnthropic = vi.fn();

// Mock external dependencies at the top level
vi.mock("@/lib/next/route-helpers", () => ({
  buildRateLimitKey: vi.fn(() => "test-key"),
}));

vi.mock("@upstash/redis", () => ({
  Redis: {
    fromEnv: vi.fn(() => ({})),
  },
}));

vi.mock("@upstash/ratelimit", () => {
  const mockInstance = {
    limit: vi.fn().mockResolvedValue({
      limit: 10,
      remaining: 9,
      reset: Date.now() + 60000,
      success: true,
    }),
  };

  return {
    Ratelimit: vi.fn().mockImplementation(() => mockInstance),
    slidingWindow: vi.fn(),
  };
});

// Mock Supabase server client to avoid env/cookie requirements
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: {
      getUser: vi.fn().mockResolvedValue({
        data: { user: { id: "u1" } },
        error: null,
      }),
    },
  })),
}));

vi.mock("@ai-sdk/openai", () => ({
  createOpenAI: mockCreateOpenAI,
}));

vi.mock("@ai-sdk/anthropic", () => ({
  createAnthropic: mockCreateAnthropic,
}));

type MockFetch = ReturnType<
  typeof vi.fn<Parameters<typeof fetch>[0], Promise<Response>>
>;

function buildProvider(fetchMock: MockFetch, url = "https://provider.test/models") {
  const config = {
    fetch: fetchMock,
    headers: vi.fn(() => ({ Authorization: "Bearer test" })),
    url: vi.fn(() => url),
  };
  const model = { config };
  const providerFn = vi.fn(() => model);
  return Object.assign(providerFn, {});
}

describe("/api/keys/validate route", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    mockCreateOpenAI.mockReset();
    mockCreateAnthropic.mockReset();
    unstubAllEnvs();
    stubRateLimitDisabled();
    // Ensure Supabase SSR client does not throw when real module is imported
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://example.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "anon-test-key");
  });

  it("returns isValid true on successful provider response", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));
    mockCreateOpenAI.mockImplementation(() => buildProvider(fetchMock));

    const { POST } = await import("../route");
    const req = {
      headers: new Headers(),
      json: async () => ({ apiKey: "sk-test", service: "openai" }),
    } as unknown as NextRequest;

    const res = await POST(req);
    const body = await res.json();

    expect(fetchMock).toHaveBeenCalledWith("https://provider.test/models", {
      headers: { Authorization: "Bearer test" },
      method: "GET",
    });
    expect({ body, status: res.status }).toEqual({
      body: { isValid: true },
      status: 200,
    });
  });

  it("returns UNAUTHORIZED when provider denies access", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({}), { status: 401 }));
    mockCreateOpenAI.mockImplementation(() => buildProvider(fetchMock));

    const { POST } = await import("../route");
    const req = {
      headers: new Headers(),
      json: async () => ({ apiKey: "sk-test", service: "openai" }),
    } as unknown as NextRequest;

    const res = await POST(req);
    const body = await res.json();

    expect({ body, status: res.status }).toEqual({
      body: { isValid: false, reason: "UNAUTHORIZED" },
      status: 200,
    });
  });

  it("returns TRANSPORT_ERROR when request fails", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    mockCreateOpenAI.mockImplementation(() => buildProvider(fetchMock));

    const { POST } = await import("../route");
    const req = {
      headers: new Headers(),
      json: async () => ({ apiKey: "sk-test", service: "openai" }),
    } as unknown as NextRequest;

    const res = await POST(req);
    const body = await res.json();

    expect({ body, status: res.status }).toEqual({
      body: { isValid: false, reason: "TRANSPORT_ERROR" },
      status: 200,
    });
  });
});
