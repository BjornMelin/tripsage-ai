/** @vitest-environment node */

import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { server } from "@/test/msw/server";
import { setupUpstashMocks } from "@/test/upstash/redis-mock";

const { redis: redisMock } = setupUpstashMocks();

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => new redisMock.Redis()),
}));

type WebSearchOutput = {
  fromCache: boolean;
  results: Array<{ title: string; url: string }>;
  tookMs: number;
};

const webSearchExecuteMock = vi.hoisted(() => vi.fn<() => Promise<WebSearchOutput>>());

vi.mock("@ai/tools/server/web-search", () => ({
  webSearch: {
    execute: webSearchExecuteMock,
  },
}));

const envStore = vi.hoisted(() => ({
  FIRECRAWL_API_KEY: "test-key",
  FIRECRAWL_BASE_URL: "https://api.firecrawl.dev/v2",
}));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVar: (key: string) => {
    const value = envStore[key as keyof typeof envStore];
    if (!value) {
      throw new Error(`Missing env ${key}`);
    }
    return value;
  },
  getServerEnvVarWithFallback: (key: string, fallback?: string) =>
    envStore[key as keyof typeof envStore] ?? fallback,
}));

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name: string, _options, fn) =>
    fn({
      addEvent: vi.fn(),
      setAttribute: vi.fn(),
    })
  ),
}));

beforeEach(() => {
  redisMock.__reset();
  webSearchExecuteMock.mockResolvedValue({
    fromCache: false,
    results: [{ title: "Example", url: "https://example.com" }],
    tookMs: 25,
  });
});

afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

describe("webSearchBatch", () => {
  test("executes webSearch for each query and normalizes results", async () => {
    const { webSearchBatch } = await import("@ai/tools/server/web-search-batch");
    const performanceNowSpy = vi
      .spyOn(performance, "now")
      .mockReturnValueOnce(0)
      .mockReturnValueOnce(10)
      .mockReturnValueOnce(22.25)
      .mockReturnValue(22.25);
    const exec = webSearchBatch.execute as
      | ((params: unknown, ctx: unknown) => Promise<unknown>)
      | undefined;
    if (!exec) {
      throw new Error("webSearchBatch.execute is undefined");
    }
    try {
      const out = await exec(
        {
          country: "de",
          limit: 2,
          queries: ["q1"],
        },
        mockContext
      );
      const outAny = unsafeCast<{
        results: Array<{
          query: string;
          ok: boolean;
          value?: {
            results: Array<{ url: string; title?: string; snippet?: string }>;
            fromCache: boolean;
            tookMs: number;
          };
        }>;
        tookMs: number;
      }>(out);
      expect(outAny.results[0].query).toBe("q1");
      expect(outAny.results[0].ok).toBe(true);
      expect(outAny.results[0].value?.results[0]?.url).toBe("https://example.com");
      expect(outAny.tookMs).toBe(12.25);
      expect(webSearchExecuteMock).toHaveBeenCalledWith(
        expect.objectContaining({ country: "DE", query: "q1" }),
        mockContext
      );
    } finally {
      performanceNowSpy.mockRestore();
    }
  });

  test("falls back to direct HTTP when webSearch throws an unexpected error", async () => {
    webSearchExecuteMock.mockRejectedValueOnce(new Error("boom"));
    let receivedBody: Record<string, unknown> | undefined;
    server.use(
      http.post("https://api.firecrawl.dev/v2/search", async ({ request }) => {
        receivedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          data: {
            web: [
              {
                description: "Fallback summary",
                title: "Fallback",
                url: "https://fallback.example.com",
              },
            ],
          },
          success: true,
        });
      })
    );

    const { webSearchBatch } = await import("@ai/tools/server/web-search-batch");
    const exec = webSearchBatch.execute as
      | ((params: unknown, ctx: unknown) => Promise<unknown>)
      | undefined;
    if (!exec) {
      throw new Error("webSearchBatch.execute is undefined");
    }

    const out = await exec(
      {
        country: "DE",
        limit: 1,
        queries: ["q1"],
      },
      mockContext
    );
    const outAny = unsafeCast<{
      results: Array<{
        query: string;
        ok: boolean;
        value?: {
          results: Array<{ url: string; title?: string; snippet?: string }>;
          fromCache: boolean;
          tookMs: number;
        };
      }>;
      tookMs: number;
    }>(out);

    expect(outAny.results[0].ok).toBe(true);
    expect(outAny.results[0].value?.results[0]?.url).toBe(
      "https://fallback.example.com"
    );
    expect(outAny.results[0].value?.results[0]?.snippet).toBe("Fallback summary");
    expect(receivedBody).toMatchObject({
      country: "DE",
      query: "q1",
    });
  });
});

describe("webSearchBatch cache key generation", () => {
  test("generates consistent cache keys for same parameters", () => {
    const params = {
      limit: 3,
      queries: ["q1", "q2"],
    };
    const key1 = canonicalizeParamsForCache(params, "web-search-batch");
    const key2 = canonicalizeParamsForCache(params, "web-search-batch");
    expect(key1).toBe(key2);
  });
});
