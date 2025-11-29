/** @vitest-environment node */

import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { server } from "@/test/msw/server";

// Hoisted mocks for all dependencies
const mockGetRedis = vi.hoisted(() => vi.fn());
const mockRatelimitLimit = vi.hoisted(() => vi.fn(async () => ({ success: true })));
const mockGetServerEnvVar = vi.hoisted(() => vi.fn(() => "test_key"));
const mockGetServerEnvVarWithFallback = vi.hoisted(() =>
  vi.fn((key: string, fallback?: string) => {
    if (key === "FIRECRAWL_API_KEY") return "test_key";
    if (key === "FIRECRAWL_BASE_URL") return fallback || "https://api.firecrawl.dev/v2";
    return fallback;
  })
);

vi.mock("@/lib/redis", () => ({
  getRedis: mockGetRedis,
}));

vi.mock("@upstash/ratelimit", () => ({
  Ratelimit: class {
    static slidingWindow(limit: number, window: string) {
      return { limit, window };
    }

    limit = mockRatelimitLimit;
  },
}));

// Telemetry shim: execute callback immediately and capture attrs via spy
const TELEMETRY_SPAN = {
  addEvent: vi.fn(),
  setAttribute: vi.fn(),
};
vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn(
    (_name: string, _opts: unknown, execute: (span: unknown) => unknown) =>
      execute(TELEMETRY_SPAN)
  ),
}));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVar: mockGetServerEnvVar,
  getServerEnvVarWithFallback: mockGetServerEnvVarWithFallback,
}));

// Static import after mocks
import { webSearch } from "@ai/tools/server/web-search";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

describe("webSearch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetRedis.mockReturnValue(null);
    mockRatelimitLimit.mockResolvedValue({ success: true });
    mockGetServerEnvVar.mockReturnValue("test_key");
    mockGetServerEnvVarWithFallback.mockImplementation(
      (key: string, fallback?: string) => {
        if (key === "FIRECRAWL_API_KEY") return "test_key";
        if (key === "FIRECRAWL_BASE_URL")
          return fallback || "https://api.firecrawl.dev/v2";
        return fallback;
      }
    );
  });

  afterEach(() => {
    server.resetHandlers();
  });

  test("validates inputs and calls Firecrawl with metadata", async () => {
    server.use(
      http.post("https://api.firecrawl.dev/v2/search", () =>
        HttpResponse.json({ results: [{ url: "https://x" }] })
      )
    );

    const out = await webSearch.execute?.(
      {
        categories: null,
        fresh: true,
        freshness: null,
        limit: 2,
        location: null,
        query: "test",
        region: null,
        scrapeOptions: null,
        sources: null,
        tbs: null,
        timeoutMs: null,
        userId: null,
      },
      mockContext
    );

    const outAny = out as unknown as {
      results: Array<{
        url: string;
        title?: string;
        snippet?: string;
        publishedAt?: string;
      }>;
      fromCache: boolean;
      tookMs: number;
    };

    expect(Array.isArray(outAny.results)).toBe(true);
    expect(outAny.results[0].url).toBe("https://x");
    expect(outAny.fromCache).toBe(false);
    expect(typeof outAny.tookMs).toBe("number");
    expect(Object.keys(outAny).sort()).toEqual(["fromCache", "results", "tookMs"]);
    expect(withTelemetrySpan).toHaveBeenCalled();
  });

  test("throws when not configured", async () => {
    // Make the env var throw to simulate missing configuration
    mockGetServerEnvVar.mockImplementation(() => {
      throw new Error("FIRECRAWL_API_KEY is not defined");
    });

    await expect(
      webSearch.execute?.(
        {
          categories: null,
          fresh: false,
          freshness: null,
          limit: 5,
          location: null,
          query: "test",
          region: null,
          scrapeOptions: null,
          sources: null,
          tbs: null,
          timeoutMs: null,
          userId: null,
        },
        mockContext
      )
    ).rejects.toMatchObject({ code: TOOL_ERROR_CODES.webSearchNotConfigured });
  });
});

describe("webSearch cache key generation", () => {
  test("generates consistent cache keys for same parameters", () => {
    const params1 = {
      categories: ["github"],
      limit: 5,
      location: "US",
      query: "test query",
      sources: ["web"],
      tbs: "qdr:d",
      timeoutMs: 5000,
    };
    const params2 = {
      categories: ["github"],
      limit: 5,
      location: "US",
      query: "test query",
      sources: ["web"],
      tbs: "qdr:d",
      timeoutMs: 5000,
    };
    const key1 = canonicalizeParamsForCache(params1, "web-search");
    const key2 = canonicalizeParamsForCache(params2, "web-search");
    expect(key1).toBe(key2);
  });
});
