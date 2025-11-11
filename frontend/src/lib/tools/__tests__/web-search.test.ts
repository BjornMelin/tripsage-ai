import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { webSearch } from "@/lib/tools/web-search";

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
  toolCallId: "test-call-id",
  messages: [],
};

test("webSearch validates inputs and calls Firecrawl", async () => {
  const mockRes = { ok: true, json: async () => ({ results: [{ url: "https://x" }] }) } as Response;
  (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
  const out = await webSearch.execute!(
    { query: "test", limit: 2, fresh: true },
    mockContext,
  );
  expect(out.results[0].url).toBe("https://x");
});

test("webSearch throws when not configured", async () => {
  process.env.FIRECRAWL_API_KEY = "";
  await expect(
    webSearch.execute!({ query: "t", limit: 5, fresh: false }, mockContext),
  ).rejects.toThrow(/web_search_not_configured/);
});

