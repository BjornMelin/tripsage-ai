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
        value?: { results: Array<{ url: string }> };
      }>;
    };

    expect(out.results).toHaveLength(3);
    expect(out.results[0].ok).toBe(true);
    const urls = out.results.flatMap((r) => r.value?.results.map((x) => x.url) ?? []);
    expect(urls).toEqual(["https://a", "https://b", "https://c"]);
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
      results: Array<{ query: string; ok: boolean; error?: { code: string } }>;
    };

    const byQuery = Object.fromEntries(out.results.map((r) => [r.query, r]));
    expect(byQuery["q-fail"].ok).toBe(false);
    expect(byQuery["q-fail"].error?.code).toMatch(/web_search_failed|web_search_error/);
    expect(byQuery["q-ok1"].ok).toBe(true);
    expect(byQuery["q-ok2"].ok).toBe(true);
  });
});
