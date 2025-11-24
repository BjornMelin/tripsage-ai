/** @vitest-environment node */

import { getTravelAdvisory } from "@ai/tools/server/travel-advisory";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

function createUpstashModule() {
  const store = new Map<string, string>();
  const getCachedJson = vi.fn(async (key: string) => {
    const val = store.get(key);
    return val ? (JSON.parse(val) as unknown) : null;
  });
  const setCachedJson = vi.fn(async (key: string, value: unknown) => {
    store.set(key, JSON.stringify(value));
  });
  const deleteCachedJson = vi.fn(async (key: string) => {
    store.delete(key);
  });
  const deleteCachedJsonMany = vi.fn(async (keys: string[]) => {
    let deleted = 0;
    keys.forEach((k) => {
      if (store.delete(k)) deleted += 1;
    });
    return deleted;
  });
  const reset = () => {
    store.clear();
    getCachedJson.mockReset();
    setCachedJson.mockReset();
    deleteCachedJson.mockReset();
    deleteCachedJsonMany.mockReset();
  };
  return {
    __reset: reset,
    deleteCachedJson,
    deleteCachedJsonMany,
    getCachedJson,
    setCachedJson,
  };
}

var upstashModule: ReturnType<typeof createUpstashModule>;

vi.mock("@/lib/cache/upstash", () => {
  upstashModule = createUpstashModule();
  return upstashModule;
});

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name: string, _options, fn) => fn()),
}));

describe("getTravelAdvisory", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    upstashModule?.__reset?.();
  });

  it("returns stub for unmappable destinations", async () => {
    if (!getTravelAdvisory.execute) {
      throw new Error("getTravelAdvisory.execute is undefined");
    }
    const result = await getTravelAdvisory.execute(
      {
        destination: "Tokyo",
      },
      mockContext
    );
    expect(result).toMatchObject({
      categories: [],
      overallScore: 75,
      provider: "stub",
    });
  });

  it("validates input schema", async () => {
    if (!getTravelAdvisory.execute) {
      throw new Error("getTravelAdvisory.execute is undefined");
    }
    await expect(
      getTravelAdvisory.execute(
        {
          destination: "",
        },
        mockContext
      )
    ).rejects.toThrow();
  });
});
