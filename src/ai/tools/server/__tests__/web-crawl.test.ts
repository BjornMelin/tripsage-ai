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
  envStore.FIRECRAWL_API_KEY = "test-key";
});

afterEach(() => {
  server.resetHandlers();
});

describe("web-crawl tools", () => {
  test("crawlUrl calls Firecrawl scrape endpoint with cost-safe defaults", async () => {
    const { crawlUrl } = await import("@ai/tools/server/web-crawl");

    let capturedBody: unknown = null;
    server.use(
      http.post("https://api.firecrawl.dev/v2/scrape", async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({ success: true, url: "https://example.com" });
      })
    );

    const execute = crawlUrl.execute;
    expect(typeof execute).toBe("function");
    if (!execute) throw new Error("crawlUrl.execute is undefined");

    const result = await execute(
      { fresh: true, scrapeOptions: null, url: "https://example.com" },
      mockContext
    );

    expect(capturedBody).toMatchObject({
      formats: ["markdown"],
      parsers: [],
      proxy: "basic",
      url: "https://example.com",
    });
    expect(result).toMatchObject({ success: true });
  });

  test("crawlUrl includes optional scrapeOptions in payload", async () => {
    const { crawlUrl } = await import("@ai/tools/server/web-crawl");

    let capturedBody: unknown = null;
    server.use(
      http.post("https://api.firecrawl.dev/v2/scrape", async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({ success: true, url: "https://example.com" });
      })
    );

    const execute = crawlUrl.execute;
    if (!execute) throw new Error("crawlUrl.execute is undefined");

    await execute(
      {
        fresh: true,
        scrapeOptions: {
          actions: [{ selector: "#accept", type: "click" }],
          formats: [
            "markdown",
            {
              prompt: "extract fields",
              schema: { title: { type: "string" } },
              type: "json",
            },
          ],
          location: { country: "US", languages: ["en"] },
          maxAge: 3600,
          onlyMainContent: true,
          parsers: ["html"],
          proxy: "basic",
        },
        url: "https://example.com",
      },
      mockContext
    );

    expect(capturedBody).toMatchObject({
      actions: [{ selector: "#accept", type: "click" }],
      formats: [
        "markdown",
        {
          prompt: "extract fields",
          schema: { title: { type: "string" } },
          type: "json",
        },
      ],
      location: { country: "US", languages: ["en"] },
      maxAge: 3600,
      onlyMainContent: true,
      parsers: ["html"],
      proxy: "basic",
      url: "https://example.com",
    });
  });

  test.each([
    [429, "web_crawl_rate_limited"],
    [401, "web_crawl_unauthorized"],
    [402, "web_crawl_payment_required"],
    [500, "web_crawl_failed"],
  ])("crawlUrl maps HTTP %s to error code", async (status, code) => {
    const { crawlUrl } = await import("@ai/tools/server/web-crawl");

    server.use(
      http.post("https://api.firecrawl.dev/v2/scrape", () =>
        HttpResponse.text("nope", { status })
      )
    );

    const execute = crawlUrl.execute;
    if (!execute) throw new Error("crawlUrl.execute is undefined");

    await expect(
      execute(
        { fresh: true, scrapeOptions: null, url: "https://example.com" },
        mockContext
      )
    ).rejects.toThrow(code);
  });

  test("crawlUrl fails closed when not configured", async () => {
    envStore.FIRECRAWL_API_KEY = "";
    const { crawlUrl } = await import("@ai/tools/server/web-crawl");

    const execute = crawlUrl.execute;
    if (!execute) throw new Error("crawlUrl.execute is undefined");

    await expect(
      execute(
        { fresh: true, scrapeOptions: null, url: "https://example.com" },
        mockContext
      )
    ).rejects.toThrow("web_crawl_not_configured");
  });

  test("crawlSite starts a crawl and returns aggregated results on completion", async () => {
    const { crawlSite } = await import("@ai/tools/server/web-crawl");

    let capturedStartBody: unknown = null;
    server.use(
      http.post("https://api.firecrawl.dev/v2/crawl", async ({ request }) => {
        capturedStartBody = await request.json();
        return HttpResponse.json({ id: "crawl-123" });
      }),
      http.get("https://api.firecrawl.dev/v2/crawl/crawl-123", () =>
        HttpResponse.json({ data: [{ url: "https://x" }], status: "completed" })
      )
    );

    const execute = crawlSite.execute;
    if (!execute) throw new Error("crawlSite.execute is undefined");

    const result = await execute(
      {
        excludePaths: null,
        fresh: true,
        includePaths: null,
        limit: 2,
        maxPages: null,
        maxResults: null,
        maxWaitTime: null,
        pollInterval: null,
        scrapeOptions: null,
        sitemap: null,
        timeoutMs: null,
        url: "https://example.com",
      },
      mockContext
    );

    expect(capturedStartBody).toMatchObject({
      limit: 2,
      scrapeOptions: { formats: ["markdown"], parsers: [], proxy: "basic" },
      url: "https://example.com",
    });
    expect(result).toMatchObject({
      data: [{ url: "https://x" }],
      next: null,
      status: "completed",
    });
  });

  test("crawlSite accepts numeric crawl id", async () => {
    const { crawlSite } = await import("@ai/tools/server/web-crawl");

    server.use(
      http.post("https://api.firecrawl.dev/v2/crawl", () =>
        HttpResponse.json({ id: 42 })
      ),
      http.get("https://api.firecrawl.dev/v2/crawl/42", () =>
        HttpResponse.json({ data: [], status: "completed" })
      )
    );

    const execute = crawlSite.execute;
    if (!execute) throw new Error("crawlSite.execute is undefined");

    await expect(
      execute(
        {
          excludePaths: null,
          fresh: true,
          includePaths: null,
          limit: 1,
          maxPages: null,
          maxResults: null,
          maxWaitTime: null,
          pollInterval: null,
          scrapeOptions: null,
          sitemap: null,
          timeoutMs: null,
          url: "https://example.com",
        },
        mockContext
      )
    ).resolves.toBeTruthy();
  });

  test("crawlSite errors when crawl id missing", async () => {
    const { crawlSite } = await import("@ai/tools/server/web-crawl");

    server.use(
      http.post("https://api.firecrawl.dev/v2/crawl", () => HttpResponse.json({})),
      http.get("https://api.firecrawl.dev/v2/crawl/undefined", () =>
        HttpResponse.json({ data: [], status: "completed" })
      )
    );

    const execute = crawlSite.execute;
    if (!execute) throw new Error("crawlSite.execute is undefined");

    await expect(
      execute(
        {
          excludePaths: null,
          fresh: true,
          includePaths: null,
          limit: 1,
          maxPages: null,
          maxResults: null,
          maxWaitTime: null,
          pollInterval: null,
          scrapeOptions: null,
          sitemap: null,
          timeoutMs: null,
          url: "https://example.com",
        },
        mockContext
      )
    ).rejects.toThrow("web_crawl_failed:no_crawl_id");
  });

  test.each([
    [429, "web_crawl_rate_limited"],
    [401, "web_crawl_unauthorized"],
    [402, "web_crawl_payment_required"],
    [500, "web_crawl_failed"],
  ])("crawlSite maps start HTTP %s to error code", async (status, code) => {
    const { crawlSite } = await import("@ai/tools/server/web-crawl");

    server.use(
      http.post("https://api.firecrawl.dev/v2/crawl", () =>
        HttpResponse.text("nope", { status })
      )
    );

    const execute = crawlSite.execute;
    if (!execute) throw new Error("crawlSite.execute is undefined");

    await expect(
      execute(
        {
          excludePaths: null,
          fresh: true,
          includePaths: null,
          limit: 1,
          maxPages: null,
          maxResults: null,
          maxWaitTime: null,
          pollInterval: null,
          scrapeOptions: null,
          sitemap: null,
          timeoutMs: null,
          url: "https://example.com",
        },
        mockContext
      )
    ).rejects.toThrow(code);
  });

  test.each([
    [429, "web_crawl_rate_limited"],
    [401, "web_crawl_unauthorized"],
    [402, "web_crawl_payment_required"],
    [500, "web_crawl_failed"],
  ])("crawlSite maps poll HTTP %s to error code", async (status, code) => {
    const { crawlSite } = await import("@ai/tools/server/web-crawl");

    server.use(
      http.post("https://api.firecrawl.dev/v2/crawl", () =>
        HttpResponse.json({ id: "crawl-123" })
      ),
      http.get("https://api.firecrawl.dev/v2/crawl/crawl-123", () =>
        HttpResponse.text("nope", { status })
      )
    );

    const execute = crawlSite.execute;
    if (!execute) throw new Error("crawlSite.execute is undefined");

    await expect(
      execute(
        {
          excludePaths: null,
          fresh: true,
          includePaths: null,
          limit: 1,
          maxPages: null,
          maxResults: null,
          maxWaitTime: null,
          pollInterval: null,
          scrapeOptions: null,
          sitemap: null,
          timeoutMs: null,
          url: "https://example.com",
        },
        mockContext
      )
    ).rejects.toThrow(code);
  });
});
