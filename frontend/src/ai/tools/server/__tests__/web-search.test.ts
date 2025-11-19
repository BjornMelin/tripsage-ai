import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(),
}));

const ratelimitLimit = vi.fn(async () => ({ success: true }));
vi.mock("@upstash/ratelimit", () => ({
  Ratelimit: class {
    static slidingWindow(limit: number, window: string) {
      return { limit, window };
    }

    limit = ratelimitLimit;
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
  getServerEnvVar: vi.fn(() => "test_key"),
  getServerEnvVarWithFallback: vi.fn((key: string, fallback?: string) => {
    if (key === "FIRECRAWL_API_KEY") return "test_key";
    if (key === "FIRECRAWL_BASE_URL") return fallback || "https://api.firecrawl.dev/v2";
    if (key === "UPSTASH_REDIS_REST_URL") return fallback;
    if (key === "UPSTASH_REDIS_REST_TOKEN") return fallback;
    return fallback;
  }),
}));

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
  ratelimitLimit.mockClear();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

describe("webSearch", () => {
  test("validates inputs and calls Firecrawl with metadata", async () => {
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
    const { webSearch } = await import("@ai/tools");
    const mockRes = {
      json: async () => ({ results: [{ url: "https://x" }] }),
      ok: true,
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
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
    const { withTelemetrySpan } = await import("@/lib/telemetry/span");
    expect(withTelemetrySpan as unknown as ReturnType<typeof vi.fn>).toHaveBeenCalled();
  });

  test("throws when not configured", async () => {
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
    const { getServerEnvVar } = await import("@/lib/env/server");
    (getServerEnvVar as ReturnType<typeof vi.fn>).mockImplementation(() => {
      throw new Error("FIRECRAWL_API_KEY is not defined");
    });
    vi.resetModules();
    const { webSearch } = await import("@ai/tools/server/web-search");
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
    (getServerEnvVar as ReturnType<typeof vi.fn>).mockReturnValue("test_key");
    vi.resetModules();
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
