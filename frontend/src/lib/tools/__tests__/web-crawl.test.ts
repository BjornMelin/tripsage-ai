/**
 * @fileoverview Unit tests for web-crawl tools (Firecrawl v2.5 API).
 */

import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { crawlSite, crawlUrl } from "../web-crawl";

const env = process.env;

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
  process.env = { ...env, FIRECRAWL_API_KEY: "test_key" };
});

afterEach(() => {
  vi.unstubAllGlobals();
  process.env = env;
});

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

test("crawlUrl validates inputs and calls Firecrawl /scrape", async () => {
  const mockRes = {
    json: async () => ({
      data: { markdown: "# Test", metadata: { title: "Test" } },
      success: true,
    }),
    ok: true,
  } as Response;
  (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
  const out = await crawlUrl.execute!(
    { fresh: true, url: "https://example.com" },
    mockContext
  );
  expect(out.success).toBe(true);
  expect(out.data.markdown).toBe("# Test");
  expect(fetch).toHaveBeenCalledWith(
    expect.stringContaining("/scrape"),
    expect.objectContaining({
      method: "POST",
    })
  );
});

test("crawlUrl applies cost-safe defaults", async () => {
  const mockRes = {
    json: async () => ({ data: {}, success: true }),
    ok: true,
  } as Response;
  (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
  await crawlUrl.execute!({ fresh: true, url: "https://example.com" }, mockContext);
  const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
  const body = JSON.parse(call[1].body as string);
  expect(body.formats).toEqual(["markdown"]);
  expect(body.parsers).toEqual([]);
  expect(body.proxy).toBe("basic");
});

test("crawlUrl throws when not configured", async () => {
  process.env.FIRECRAWL_API_KEY = "";
  await expect(
    crawlUrl.execute!({ fresh: false, url: "https://example.com" }, mockContext)
  ).rejects.toThrow(/web_crawl_not_configured/);
});

test("crawlSite validates inputs and starts crawl", async () => {
  const startMock = {
    json: async () => ({
      id: "crawl-123",
      success: true,
      url: "https://api.firecrawl.dev/v2/crawl/crawl-123",
    }),
    ok: true,
  } as Response;
  const statusMock = {
    json: async () => ({
      completed: 5,
      data: [{ markdown: "# Page 1" }],
      status: "completed",
      total: 5,
    }),
    ok: true,
  } as Response;
  (fetch as unknown as ReturnType<typeof vi.fn>)
    .mockResolvedValueOnce(startMock)
    .mockResolvedValue(statusMock);
  const out = (await crawlSite.execute!(
    { fresh: true, limit: 5, url: "https://example.com" },
    mockContext
  )) as { status: string; data: unknown[] };
  expect(out.status).toBe("completed");
  expect(out.data).toHaveLength(1);
  expect(fetch).toHaveBeenCalledWith(
    expect.stringContaining("/crawl"),
    expect.objectContaining({
      method: "POST",
    })
  );
});

test("crawlSite applies cost-safe defaults in scrapeOptions", async () => {
  const startMock = {
    json: async () => ({ id: "crawl-123", success: true }),
    ok: true,
  } as Response;
  const statusMock = {
    json: async () => ({ data: [], status: "completed" }),
    ok: true,
  } as Response;
  (fetch as unknown as ReturnType<typeof vi.fn>)
    .mockResolvedValueOnce(startMock)
    .mockResolvedValue(statusMock);
  await crawlSite.execute!(
    { fresh: true, limit: 5, url: "https://example.com" },
    mockContext
  );
  const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
  const body = JSON.parse(call[1].body as string);
  expect(body.scrapeOptions.formats).toEqual(["markdown"]);
  expect(body.scrapeOptions.parsers).toEqual([]);
  expect(body.scrapeOptions.proxy).toBe("basic");
});

test("crawlSite throws when not configured", async () => {
  process.env.FIRECRAWL_API_KEY = "";
  await expect(
    crawlSite.execute!(
      { fresh: false, limit: 5, url: "https://example.com" },
      mockContext
    )
  ).rejects.toThrow(/web_crawl_not_configured/);
});

test("crawlSite handles rate limit errors", async () => {
  const startMock = {
    ok: false,
    status: 429,
    text: async () => "Rate limit exceeded",
  } as Response;
  (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(startMock);
  await expect(
    crawlSite.execute!(
      { fresh: true, limit: 5, url: "https://example.com" },
      mockContext
    )
  ).rejects.toThrow(/web_crawl_rate_limited/);
});

test("crawlSite handles unauthorized errors", async () => {
  const startMock = {
    ok: false,
    status: 401,
    text: async () => "Unauthorized",
  } as Response;
  (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(startMock);
  await expect(
    crawlSite.execute!(
      { fresh: true, limit: 5, url: "https://example.com" },
      mockContext
    )
  ).rejects.toThrow(/web_crawl_unauthorized/);
});

test("crawlSite respects maxPages limit", async () => {
  const startMock = {
    json: async () => ({ id: "crawl-123", success: true }),
    ok: true,
  } as Response;
  const statusMock = {
    json: async () => ({
      completed: 10,
      data: Array(10).fill({ markdown: "# Page" }),
      next: "https://api.firecrawl.dev/v2/crawl/crawl-123?skip=10",
      status: "scraping",
      total: 100,
    }),
    ok: true,
  } as Response;
  (fetch as unknown as ReturnType<typeof vi.fn>)
    .mockResolvedValueOnce(startMock)
    .mockResolvedValue(statusMock);
  const out = (await crawlSite.execute!(
    { fresh: true, limit: 50, maxPages: 1, url: "https://example.com" },
    mockContext
  )) as { status: string; data: unknown[] };
  expect(out.data).toHaveLength(10);
  expect(out.status).toBe("scraping");
});

test("crawlUrl supports custom scrapeOptions", async () => {
  const mockRes = {
    json: async () => ({ data: {}, success: true }),
    ok: true,
  } as Response;
  (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
  await crawlUrl.execute!(
    {
      fresh: true,
      scrapeOptions: {
        formats: ["markdown", "html"],
        proxy: "stealth",
      },
      url: "https://example.com",
    },
    mockContext
  );
  const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
  const body = JSON.parse(call[1].body as string);
  expect(body.formats).toEqual(["markdown", "html"]);
  expect(body.proxy).toBe("stealth");
  expect(body.parsers).toEqual([]);
});

test("crawlSite supports includePaths and excludePaths", async () => {
  const startMock = {
    json: async () => ({ id: "crawl-123", success: true }),
    ok: true,
  } as Response;
  const statusMock = {
    json: async () => ({ data: [], status: "completed" }),
    ok: true,
  } as Response;
  (fetch as unknown as ReturnType<typeof vi.fn>)
    .mockResolvedValueOnce(startMock)
    .mockResolvedValue(statusMock);
  await crawlSite.execute!(
    {
      excludePaths: ["/admin/*"],
      fresh: true,
      includePaths: ["/blog/*"],
      limit: 10,
      url: "https://example.com",
    },
    mockContext
  );
  const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
  const body = JSON.parse(call[1].body as string);
  expect(body.includePaths).toEqual(["/blog/*"]);
  expect(body.excludePaths).toEqual(["/admin/*"]);
});
