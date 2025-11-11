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
  messages: [],
  toolCallId: "test-call-id",
};

test("webSearch validates inputs and calls Firecrawl", async () => {
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

test("webSearch throws when not configured", async () => {
  process.env.FIRECRAWL_API_KEY = "";
  await expect(
    webSearch.execute?.({ fresh: false, limit: 5, query: "t" }, mockContext)
  ).rejects.toThrow(/web_search_not_configured/);
});
