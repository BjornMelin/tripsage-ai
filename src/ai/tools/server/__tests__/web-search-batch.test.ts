/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(),
}));

vi.mock("@ai/tools/server/web-search", () => ({
  webSearch: {
    execute: vi.fn(async () => ({
      fromCache: false,
      results: [{ title: "Example", url: "https://example.com" }],
      tookMs: 25,
    })),
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

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

describe("webSearchBatch", () => {
  test("normalizes Firecrawl batch responses", async () => {
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
    const { webSearchBatch } = await import("@ai/tools/server/web-search-batch");
    const mockRes = {
      json: async () => ({
        results: [
          {
            query: "q1",
            results: [{ title: "Example", url: "https://example.com" }],
          },
        ],
      }),
      ok: true,
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    const exec = webSearchBatch.execute as
      | ((params: unknown, ctx: unknown) => Promise<unknown>)
      | undefined;
    if (!exec) {
      throw new Error("webSearchBatch.execute is undefined");
    }
    const out = await exec(
      {
        limit: 2,
        queries: ["q1"],
      },
      mockContext
    );
    const outAny = out as unknown as {
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
    };
    expect(outAny.results[0].query).toBe("q1");
    expect(outAny.results[0].value?.results[0]?.url).toBe("https://example.com");
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
