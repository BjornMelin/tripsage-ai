import { beforeEach, describe, expect, it, vi } from "vitest";
import * as route from "@/app/api/embeddings/route";
import { createMockNextRequest } from "@/test/route-helpers";

vi.mock("ai", () => ({
  embed: vi.fn(async () => ({
    embedding: Array.from({ length: 1536 }, () => Math.random()),
    usage: { tokens: { input: 12 } },
  })),
}));

const UPSERT = vi.fn();
const FROM = vi.fn(() => ({ upsert: UPSERT }));

vi.mock("@/lib/supabase/admin", () => ({
  createAdminSupabase: vi.fn(() => ({
    from: FROM,
  })),
}));

beforeEach(() => {
  UPSERT.mockReset();
  FROM.mockClear();
  UPSERT.mockResolvedValue({ error: null });
});

describe("POST /api/embeddings", () => {
  it("returns 400 on missing input", async () => {
    const res = await route.POST(
      createMockNextRequest({
        body: { text: "" },
        method: "POST",
        url: "http://localhost/api/embeddings",
      })
    );
    expect(res.status).toBe(400);
  });

  it("returns 1536-d embedding", async () => {
    const res = await route.POST(
      createMockNextRequest({
        body: { text: "hello world" },
        method: "POST",
        url: "http://localhost/api/embeddings",
      })
    );
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(Array.isArray(json.embedding)).toBe(true);
    expect(json.embedding).toHaveLength(1536);
    expect(json.success).toBe(true);
    expect(json.persisted).toBe(false);
    expect(FROM).not.toHaveBeenCalled();
  });

  it("persists accommodation embeddings when property metadata present", async () => {
    const res = await route.POST(
      createMockNextRequest({
        body: {
          property: {
            amenities: ["pool", "wifi"],
            description: "Beautiful stay",
            id: "prop-123",
            name: "Test Property",
            source: "hotel",
          },
        },
        method: "POST",
        url: "http://localhost/api/embeddings",
      })
    );

    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.persisted).toBe(true);
    expect(FROM).toHaveBeenCalledWith("accommodation_embeddings");
    expect(UPSERT).toHaveBeenCalledWith(
      expect.objectContaining({
        amenities: "pool, wifi",
        id: "prop-123",
        source: "hotel",
      }),
      { onConflict: "id" }
    );
  });

  it("logs and continues when persistence fails", async () => {
    UPSERT.mockResolvedValueOnce({ error: { message: "boom" } });
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);

    const res = await route.POST(
      createMockNextRequest({
        body: {
          property: {
            id: "prop-999",
            name: "fail",
          },
        },
        method: "POST",
        url: "http://localhost/api/embeddings",
      })
    );

    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.persisted).toBe(false);
    expect(consoleError).toHaveBeenCalled();
    consoleError.mockRestore();
  });
});
