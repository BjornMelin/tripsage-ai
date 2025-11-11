import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(),
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
  test("validates inputs and calls Firecrawl", async () => {
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
    expect(out.results[0].url).toBe("https://x");
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
        limit: 10,
        location: "US",
        query: "test query",
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
    expect(body.tbs).toBe("qdr:d");
    expect(body.timeout).toBe(5000);
    expect(body.scrapeOptions).toEqual({
      formats: ["html", "markdown"],
      parsers: ["pdf"],
      proxy: "stealth",
    });
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
  test("returns cached result when available and fresh=false", async () => {
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
    expect(result).toEqual({ cached: true, results: [] });
    expect(fetch).not.toHaveBeenCalled();
    expect(mockRedis.get).toHaveBeenCalled();
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
