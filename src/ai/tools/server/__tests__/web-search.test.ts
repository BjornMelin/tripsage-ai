/** @vitest-environment node */

import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import { HttpResponse, http } from "msw";
import {
  afterAll,
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  test,
  vi,
} from "vitest";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { server } from "@/test/msw/server";
import { setupUpstashTestEnvironment } from "@/test/upstash/setup";

const { afterAllHook: upstashAfterAllHook, beforeEachHook: upstashBeforeEachHook } =
  setupUpstashTestEnvironment();

// Hoisted mocks for all dependencies
const mockGetRedis = vi.hoisted(() => vi.fn());
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

let webSearch: typeof import("@ai/tools/server/web-search").webSearch;

import { withTelemetrySpan } from "@/lib/telemetry/span";

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

describe("webSearch", () => {
  beforeAll(async () => {
    ({ webSearch } = await import("@ai/tools/server/web-search"));
  });

  beforeEach(() => {
    upstashBeforeEachHook();
    vi.clearAllMocks();
    mockGetRedis.mockReturnValue(null);
    mockGetServerEnvVar.mockReturnValue("test_key");
  });

  afterEach(() => {
    server.resetHandlers();
  });

  test("validates inputs and calls Firecrawl with metadata", async () => {
    let receivedBody: Record<string, unknown> | undefined;
    server.use(
      http.post("https://api.firecrawl.dev/v2/search", async ({ request }) => {
        receivedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ results: [{ url: "https://x" }] });
      })
    );

    const execute = webSearch.execute;
    expect(typeof execute).toBe("function");

    if (!execute) throw new Error("webSearch.execute is undefined");

    const out = await execute(
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

    const outAny = unsafeCast<{
      results: Array<{
        url: string;
        title?: string;
        snippet?: string;
        publishedAt?: string;
      }>;
      fromCache: boolean;
      tookMs: number;
    }>(out);

    expect(Array.isArray(outAny.results)).toBe(true);
    expect(outAny.results[0].url).toBe("https://x");
    expect(outAny.fromCache).toBe(false);
    expect(typeof outAny.tookMs).toBe("number");
    expect(Object.keys(outAny).sort()).toEqual(["fromCache", "results", "tookMs"]);
    expect(withTelemetrySpan).toHaveBeenCalled();
    expect(receivedBody).toBeDefined();
    expect(receivedBody).toMatchObject({
      limit: 2,
      query: "test",
    });
  });

  test("throws when not configured", async () => {
    // Make the env var throw to simulate missing configuration
    mockGetServerEnvVar.mockImplementation(() => {
      throw new Error("FIRECRAWL_API_KEY is not defined");
    });

    const execute = webSearch.execute;
    expect(typeof execute).toBe("function");

    if (!execute) throw new Error("webSearch.execute is undefined");

    await expect(
      execute(
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

  afterAll(() => {
    upstashAfterAllHook();
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
