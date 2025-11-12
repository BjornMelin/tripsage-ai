import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_n: string, _o: unknown, fn: (s: unknown) => unknown) =>
    fn({})
  ),
}));

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => null),
}));

const mockContext = { messages: [], toolCallId: "tc-1" };

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
  process.env.FIRECRAWL_API_KEY = "test_key";
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("webSearchBatch", () => {
  test("normalizes batch results with extra fields", async () => {
    vi.resetModules();
    const { webSearchBatch } = await import("@/lib/tools/web-search-batch");
    // Firecrawl may return extra fields
    const mockRes = {
      json: async () => ({
        results: [
          {
            content: "extra",
            score: 0.9,
            title: "Example",
            url: "https://example.com",
          },
        ],
      }),
      ok: true,
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    const out = (await webSearchBatch.execute?.(
      { queries: ["test"] },
      mockContext
    )) as unknown as {
      results: Array<{
        query: string;
        ok: boolean;
        value?: {
          results: Array<{
            url: string;
            title?: string;
            snippet?: string;
            publishedAt?: string;
          }>;
          fromCache: boolean;
          tookMs: number;
        };
        error?: { code: string; message?: string };
      }>;
      tookMs: number;
    };
    expect(out.results[0].ok).toBe(true);
    expect(out.results[0].value?.results[0].url).toBe("https://example.com");
    expect(out.results[0].value?.results[0].title).toBe("Example");
    // Ensure extra fields are normalized out
    expect("content" in (out.results[0].value?.results[0] ?? {})).toBe(false);
    expect("score" in (out.results[0].value?.results[0] ?? {})).toBe(false);
    expect(Object.keys(out.results[0].value?.results[0] ?? {}).sort()).toEqual([
      "title",
      "url",
    ]);
  });

  test("runs multiple queries and aggregates results", async () => {
    vi.resetModules();
    const { webSearchBatch } = await import("@/lib/tools/web-search-batch");

    const mk = (url: string) =>
      ({ json: async () => ({ results: [{ url }] }), ok: true }) as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(mk("https://a"))
      .mockResolvedValueOnce(mk("https://b"))
      .mockResolvedValueOnce(mk("https://c"));

    const out = (await webSearchBatch.execute?.(
      { limit: 2, queries: ["q1", "q2", "q3"] },
      mockContext
    )) as unknown as {
      results: Array<{
        query: string;
        ok: boolean;
        value?: {
          results: Array<{
            url: string;
            title?: string;
            snippet?: string;
            publishedAt?: string;
          }>;
          fromCache: boolean;
          tookMs: number;
        };
        error?: { code: string; message?: string };
      }>;
      tookMs: number;
    };

    // Assert strict output shape: results array, tookMs number
    expect(Array.isArray(out.results)).toBe(true);
    expect(out.results).toHaveLength(3);
    expect(out.results[0].ok).toBe(true);
    expect(typeof out.tookMs).toBe("number");
    // Ensure each result has strict shape
    for (const r of out.results) {
      expect(typeof r.ok).toBe("boolean");
      expect(typeof r.query).toBe("string");
      if (r.ok) {
        expect(r.value).toBeDefined();
        expect(Array.isArray(r.value?.results)).toBe(true);
        expect(typeof r.value?.fromCache).toBe("boolean");
        expect(typeof r.value?.tookMs).toBe("number");
      }
    }
    const urls = out.results.flatMap((r) => r.value?.results.map((x) => x.url) ?? []);
    expect(urls).toEqual(["https://a", "https://b", "https://c"]);
    // Ensure no extra fields beyond schema
    expect(Object.keys(out).sort()).toEqual(["results", "tookMs"]);
  });

  test("collects errors per query without failing the batch", async () => {
    vi.resetModules();
    const { webSearchBatch } = await import("@/lib/tools/web-search-batch");
    const ok = {
      json: async () => ({ results: [{ url: "https://ok" }] }),
      ok: true,
    } as Response;
    const fail = { ok: false, status: 500, text: async () => "boom" } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(ok)
      .mockResolvedValueOnce(fail)
      .mockResolvedValueOnce(ok);

    const out = (await webSearchBatch.execute?.(
      { queries: ["q-ok1", "q-fail", "q-ok2"] },
      mockContext
    )) as unknown as {
      results: Array<{
        query: string;
        ok: boolean;
        value?: {
          results: Array<{
            url: string;
            title?: string;
            snippet?: string;
            publishedAt?: string;
          }>;
          fromCache: boolean;
          tookMs: number;
        };
        error?: { code: string; message?: string };
      }>;
      tookMs: number;
    };

    // Assert strict output shape for error paths
    expect(Array.isArray(out.results)).toBe(true);
    expect(typeof out.tookMs).toBe("number");
    const byQuery = Object.fromEntries(out.results.map((r) => [r.query, r]));
    expect(byQuery["q-fail"].ok).toBe(false);
    expect(byQuery["q-fail"].error?.code).toMatch(/web_search_failed|web_search_error/);
    expect(byQuery["q-ok1"].ok).toBe(true);
    expect(byQuery["q-ok2"].ok).toBe(true);
    // Ensure error result has strict shape
    expect(typeof byQuery["q-fail"].error?.code).toBe("string");
    // Ensure success results have strict shape
    if (byQuery["q-ok1"].value) {
      expect(Array.isArray(byQuery["q-ok1"].value.results)).toBe(true);
      expect(typeof byQuery["q-ok1"].value.fromCache).toBe("boolean");
      expect(typeof byQuery["q-ok1"].value.tookMs).toBe("number");
    }
  });
});
