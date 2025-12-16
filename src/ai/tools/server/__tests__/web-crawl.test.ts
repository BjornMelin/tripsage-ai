/** @vitest-environment node */

import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { server } from "@/test/msw/server";

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => undefined),
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
  vi.clearAllMocks();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("web-crawl tool", () => {
  test("calls Firecrawl crawl endpoint with correct payload", async () => {
    const { webSearch } = await import("@ai/tools/server/web-search");

    let capturedBody: unknown = null;
    server.use(
      http.post("https://api.firecrawl.dev/v2/search", async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({ results: [] });
      })
    );

    await webSearch.execute?.(
      {
        categories: null,
        fresh: true,
        freshness: null,
        limit: 1,
        location: null,
        query: "test site",
        region: null,
        scrapeOptions: null,
        sources: ["web"],
        tbs: null,
        timeoutMs: null,
        userId: null,
      },
      mockContext
    );
    expect(capturedBody).toMatchObject({
      limit: 1,
      query: "test site",
      sources: ["web"],
    });
  });
});
