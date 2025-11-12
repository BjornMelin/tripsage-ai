import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(),
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

const env = process.env;

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
  process.env = { ...env, FIRECRAWL_API_KEY: "test_key" };
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
  process.env = env;
});

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

describe("webSearch", () => {
  test("validates inputs and calls Firecrawl with metadata", async () => {
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
    const { webSearch } = await import("@/lib/tools/web-search");
    const mockRes = {
      json: async () => ({ results: [{ url: "https://x" }] }),
      ok: true,
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    const out = await webSearch.execute?.(
      { fresh: true, limit: 2, query: "test" },
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
    // Assert strict output shape: results array, fromCache boolean, tookMs number
    expect(Array.isArray(outAny.results)).toBe(true);
    expect(outAny.results[0].url).toBe("https://x");
    expect(outAny.fromCache).toBe(false);
    expect(typeof outAny.tookMs).toBe("number");
    // Ensure no extra fields beyond schema
    expect(Object.keys(outAny).sort()).toEqual(["fromCache", "results", "tookMs"]);
    const { withTelemetrySpan } = await import("@/lib/telemetry/span");
    expect(withTelemetrySpan as unknown as ReturnType<typeof vi.fn>).toHaveBeenCalled();
  });

  test("normalizes Firecrawl responses with extra fields", async () => {
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
    const { webSearch } = await import("@/lib/tools/web-search");
    // Firecrawl may return extra fields like content, score, source
    const mockRes = {
      json: async () => ({
        results: [
          {
            content: "extra content field",
            score: 0.95,
            snippet: "Test snippet",
            source: "firecrawl",
            title: "Example",
            url: "https://example.com",
          },
        ],
      }),
      ok: true,
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    const out = await webSearch.execute?.(
      { fresh: true, limit: 5, query: "test" },
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
    // Assert normalized output excludes extra fields
    expect(Array.isArray(outAny.results)).toBe(true);
    expect(outAny.results).toHaveLength(1);
    expect(outAny.results[0].url).toBe("https://example.com");
    expect(outAny.results[0].title).toBe("Example");
    expect(outAny.results[0].snippet).toBe("Test snippet");
    // Ensure extra fields are not present
    expect("content" in outAny.results[0]).toBe(false);
    expect("score" in outAny.results[0]).toBe(false);
    expect("source" in outAny.results[0]).toBe(false);
    // Ensure strict schema compliance
    expect(Object.keys(outAny.results[0]).sort()).toEqual(["snippet", "title", "url"]);
    expect(Object.keys(outAny).sort()).toEqual(["fromCache", "results", "tookMs"]);
  });

  test("throws when not configured", async () => {
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
    const { webSearch } = await import("@/lib/tools/web-search");
    process.env.FIRECRAWL_API_KEY = "";
    await expect(
      webSearch.execute?.({ fresh: false, limit: 5, query: "test" }, mockContext)
    ).rejects.toThrow(/web_search_not_configured/);
  });

  test("handles rate limit errors", async () => {
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
    const { webSearch } = await import("@/lib/tools/web-search");
    const mockRes = {
      ok: false,
      status: 429,
      text: async () => "Rate limited",
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    await expect(
      webSearch.execute?.({ fresh: true, limit: 5, query: "test" }, mockContext)
    ).rejects.toThrow(/web_search_rate_limited/);
  });

  test("handles unauthorized errors", async () => {
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
    const { webSearch } = await import("@/lib/tools/web-search");
    const mockRes = {
      ok: false,
      status: 401,
      text: async () => "Unauthorized",
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    await expect(
      webSearch.execute?.({ fresh: true, limit: 5, query: "test" }, mockContext)
    ).rejects.toThrow(/web_search_unauthorized/);
  });

  test("handles payment required errors", async () => {
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
    const { webSearch } = await import("@/lib/tools/web-search");
    const mockRes = {
      ok: false,
      status: 402,
      text: async () => "Payment required",
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    await expect(
      webSearch.execute?.({ fresh: true, limit: 5, query: "test" }, mockContext)
    ).rejects.toThrow(/web_search_payment_required/);
  });

  test("handles generic API errors", async () => {
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
    const { webSearch } = await import("@/lib/tools/web-search");
    const mockRes = {
      ok: false,
      status: 500,
      text: async () => "Internal server error",
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    await expect(
      webSearch.execute?.({ fresh: true, limit: 5, query: "test" }, mockContext)
    ).rejects.toThrow(/web_search_failed/);
  });

  test("uses custom base URL when configured", async () => {
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
    const { webSearch } = await import("@/lib/tools/web-search");
    process.env.FIRECRAWL_BASE_URL = "https://custom.firecrawl.dev/v2";
    const mockRes = {
      json: async () => ({ results: [] }),
      ok: true,
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    await webSearch.execute?.({ fresh: true, limit: 5, query: "test" }, mockContext);
    expect(fetch).toHaveBeenCalledWith(
      "https://custom.firecrawl.dev/v2/search",
      expect.any(Object)
    );
  });

  test("builds request body with all parameters", async () => {
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
    const { webSearch } = await import("@/lib/tools/web-search");
    const mockRes = {
      json: async () => ({ results: [] }),
      ok: true,
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    await webSearch.execute?.(
      {
        categories: ["github", "research"],
        fresh: true,
        freshness: "d7", // UNVERIFIED
        limit: 10,
        location: "US",
        query: "test query",
        region: "us", // UNVERIFIED
        scrapeOptions: {
          formats: ["markdown", "html"],
          parsers: ["pdf"],
          proxy: "stealth",
        },
        sources: ["web", "news"],
        tbs: "qdr:d",
        timeoutMs: 5000,
      },
      mockContext
    );
    const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body as string);
    expect(body.query).toBe("test query");
    expect(body.limit).toBe(10);
    expect(body.sources).toEqual(["web", "news"]);
    expect(body.categories).toEqual(["github", "research"]);
    expect(body.location).toBe("US");
    expect(body.region).toBe("us");
    expect(body.freshness).toBe("d7");
    expect(body.tbs).toBe("qdr:d");
    expect(body.timeout).toBe(5000);
    expect(body.scrapeOptions).toEqual({
      formats: ["html", "markdown"],
      parsers: ["pdf"],
      proxy: "stealth",
    });
  });

  test("accepts custom categories strings", async () => {
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
    const { webSearch } = await import("@/lib/tools/web-search");
    const mockRes = {
      json: async () => ({ results: [] }),
      ok: true,
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    await webSearch.execute?.(
      {
        categories: ["custom-cat", "github"],
        fresh: true,
        limit: 3,
        query: "test",
      },
      mockContext
    );
    const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body as string);
    expect(body.categories).toEqual(["custom-cat", "github"]);
  });

  test("applies cost-safe defaults for scrapeOptions", async () => {
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
    const { webSearch } = await import("@/lib/tools/web-search");
    const mockRes = {
      json: async () => ({ results: [] }),
      ok: true,
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    await webSearch.execute?.(
      {
        fresh: true,
        limit: 5,
        query: "test",
        scrapeOptions: {
          formats: ["markdown"],
        },
      },
      mockContext
    );
    const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body as string);
    expect(body.scrapeOptions).toEqual({
      formats: ["markdown"],
      parsers: [],
      proxy: "basic",
    });
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
    const key1 = canonicalizeParamsForCache(params1, "ws");
    const key2 = canonicalizeParamsForCache(params2, "ws");
    expect(key1).toBe(key2);
  });

  test("generates different cache keys for different queries", () => {
    const params1 = {
      limit: 5,
      query: "test query 1",
      sources: ["web"],
    };
    const params2 = {
      limit: 5,
      query: "test query 2",
      sources: ["web"],
    };
    const key1 = canonicalizeParamsForCache(params1, "ws");
    const key2 = canonicalizeParamsForCache(params2, "ws");
    expect(key1).not.toBe(key2);
  });

  test("generates different cache keys for different limits", () => {
    const params1 = {
      limit: 5,
      query: "test",
      sources: ["web"],
    };
    const params2 = {
      limit: 10,
      query: "test",
      sources: ["web"],
    };
    const key1 = canonicalizeParamsForCache(params1, "ws");
    const key2 = canonicalizeParamsForCache(params2, "ws");
    expect(key1).not.toBe(key2);
  });

  test("handles scrapeOptions in cache key generation", () => {
    const params1 = {
      limit: 5,
      query: "test",
      scrapeOptionsFormats: ["markdown"],
      scrapeOptionsParsers: ["pdf"],
      scrapeOptionsProxy: "stealth",
      sources: ["web"],
    };
    const params2 = {
      limit: 5,
      query: "test",
      scrapeOptionsFormats: ["markdown"],
      scrapeOptionsParsers: ["pdf"],
      scrapeOptionsProxy: "stealth",
      sources: ["web"],
    };
    const key1 = canonicalizeParamsForCache(params1, "ws");
    const key2 = canonicalizeParamsForCache(params2, "ws");
    expect(key1).toBe(key2);
  });

  test("ignores undefined/null values in cache key", () => {
    const params1 = {
      limit: 5,
      query: "test",
      sources: ["web"],
    };
    const params2 = {
      categories: undefined,
      limit: 5,
      location: undefined,
      query: "test",
      sources: ["web"],
      tbs: undefined,
      timeoutMs: undefined,
    };
    const key1 = canonicalizeParamsForCache(params1, "ws");
    const key2 = canonicalizeParamsForCache(params2, "ws");
    expect(key1).toBe(key2);
  });

  test("normalizes query to lowercase in cache key", () => {
    const params1 = {
      limit: 5,
      query: "Test Query",
      sources: ["web"],
    };
    const params2 = {
      limit: 5,
      query: "test query",
      sources: ["web"],
    };
    const key1 = canonicalizeParamsForCache(params1, "ws");
    const key2 = canonicalizeParamsForCache(params2, "ws");
    expect(key1).toBe(key2);
  });

  test("sorts array values in cache key", () => {
    const params1 = {
      categories: ["github", "research"],
      limit: 5,
      query: "test",
      sources: ["web", "news"],
    };
    const params2 = {
      categories: ["research", "github"],
      limit: 5,
      query: "test",
      sources: ["news", "web"],
    };
    const key1 = canonicalizeParamsForCache(params1, "ws");
    const key2 = canonicalizeParamsForCache(params2, "ws");
    expect(key1).toBe(key2);
  });
});

describe("webSearch caching behavior", () => {
  test("normalizes cached results with extra fields", async () => {
    const { getRedis } = await import("@/lib/redis");
    const mockRedis = {
      get: vi.fn().mockResolvedValue({
        results: [
          {
            content: "extra",
            score: 0.8,
            title: "Cached",
            url: "https://cached.com",
          },
        ],
      }),
    };
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(mockRedis);
    const { webSearch } = await import("@/lib/tools/web-search");
    const result = await webSearch.execute?.(
      { fresh: false, limit: 5, query: "test" },
      mockContext
    );
    const resAny = result as unknown as {
      results: Array<{
        url: string;
        title?: string;
        snippet?: string;
        publishedAt?: string;
      }>;
      fromCache: boolean;
      tookMs: number;
    };
    expect(Array.isArray(resAny.results)).toBe(true);
    expect(resAny.results[0].url).toBe("https://cached.com");
    expect(resAny.results[0].title).toBe("Cached");
    // Ensure extra fields are normalized out
    expect("content" in resAny.results[0]).toBe(false);
    expect("score" in resAny.results[0]).toBe(false);
    expect(resAny.fromCache).toBe(true);
    expect(typeof resAny.tookMs).toBe("number");
    expect(Object.keys(resAny.results[0]).sort()).toEqual(["title", "url"]);
    expect(Object.keys(resAny).sort()).toEqual(["fromCache", "results", "tookMs"]);
  });

  test("returns cached result when available and fresh=false with metadata", async () => {
    const { getRedis } = await import("@/lib/redis");
    const mockRedis = {
      get: vi.fn().mockResolvedValue({ cached: true, results: [] }),
      set: vi.fn(),
    };
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(mockRedis);
    const { webSearch } = await import("@/lib/tools/web-search");
    const mockRes = {
      json: async () => ({ results: [] }),
      ok: true,
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    const result = await webSearch.execute?.(
      { fresh: false, limit: 5, query: "test" },
      mockContext
    );
    const resAny = result as unknown as {
      results: Array<{
        url: string;
        title?: string;
        snippet?: string;
        publishedAt?: string;
      }>;
      fromCache: boolean;
      tookMs: number;
    };
    // Assert strict output shape for cached results
    expect(Array.isArray(resAny.results)).toBe(true);
    expect(resAny.results).toEqual([]);
    expect(resAny.fromCache).toBe(true);
    expect(typeof resAny.tookMs).toBe("number");
    // Ensure no extra fields beyond schema
    expect(Object.keys(resAny).sort()).toEqual(["fromCache", "results", "tookMs"]);
    expect(fetch).not.toHaveBeenCalled();
    expect(mockRedis.get).toHaveBeenCalled();
  });

  test("rate limiting calls Upstash when configured", async () => {
    // Provide Upstash envs to construct limiter
    process.env.UPSTASH_REDIS_REST_URL = "https://upstash.example";
    process.env.UPSTASH_REDIS_REST_TOKEN = "token";

    vi.doMock("@upstash/redis", () => ({
      Redis: { fromEnv: () => ({}) },
    }));

    const limitSpy = vi.fn(async () => ({
      limit: 20,
      remaining: 19,
      reset: Math.floor(Date.now() / 1000) + 60,
      success: true,
    }));
    const ctorSpy = vi.fn().mockImplementation(function () {
      // @ts-expect-error - attach instance method dynamically for test
      this.limit = limitSpy;
    });
    vi.resetModules();
    vi.doMock("@upstash/ratelimit", () => ({
      Ratelimit: Object.assign(ctorSpy, { slidingWindow: () => ({}) }),
    }));

    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
    const { webSearch } = await import("@/lib/tools/web-search");
    const mockRes = { json: async () => ({ results: [] }), ok: true } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    await webSearch.execute?.(
      { fresh: true, limit: 1, query: "foo", userId: "u1" },
      mockContext
    );
    expect(ctorSpy).toHaveBeenCalled();
    expect(limitSpy).toHaveBeenCalledWith("u1");
  });

  test("bypasses cache when fresh=true", async () => {
    const { getRedis } = await import("@/lib/redis");
    const mockRedis = {
      get: vi.fn(),
      set: vi.fn(),
    };
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(mockRedis);
    const { webSearch } = await import("@/lib/tools/web-search");
    const mockRes = {
      json: async () => ({ results: [] }),
      ok: true,
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    await webSearch.execute?.({ fresh: true, limit: 5, query: "test" }, mockContext);
    expect(fetch).toHaveBeenCalled();
    expect(mockRedis.get).not.toHaveBeenCalled();
  });

  test("caches successful results", async () => {
    const { getRedis } = await import("@/lib/redis");
    const mockRedis = {
      get: vi.fn().mockResolvedValue(null),
      set: vi.fn(),
    };
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(mockRedis);
    const { webSearch } = await import("@/lib/tools/web-search");
    const mockData = { results: [{ url: "https://example.com" }] };
    const mockRes = {
      json: async () => mockData,
      ok: true,
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    await webSearch.execute?.({ fresh: false, limit: 5, query: "test" }, mockContext);
    expect(mockRedis.set).toHaveBeenCalledWith(
      expect.stringContaining("ws:"),
      mockData,
      { ex: 3600 }
    );
  });

  test("handles missing Redis gracefully", async () => {
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
    const { webSearch } = await import("@/lib/tools/web-search");
    const mockRes = {
      json: async () => ({ results: [] }),
      ok: true,
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    await expect(
      webSearch.execute?.({ fresh: false, limit: 5, query: "test" }, mockContext)
    ).resolves.toBeDefined();
    expect(fetch).toHaveBeenCalled();
  });
});
