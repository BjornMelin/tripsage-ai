/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import * as route from "@/app/api/embeddings/route";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/route-helpers";

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

// Mock Supabase server client
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: {
      getUser: async () => ({
        data: { user: { id: "user-1" } },
      }),
    },
  })),
}));

// Mock Redis
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => Promise.resolve({})),
}));

const loggerErrorMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: vi.fn(() => ({
    debug: vi.fn(),
    error: loggerErrorMock,
    info: vi.fn(),
    warn: vi.fn(),
  })),
}));

// Mock route helpers
vi.mock("@/lib/next/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/next/route-helpers")>(
    "@/lib/next/route-helpers"
  );
  return {
    ...actual,
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});

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

describe("/api/embeddings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    UPSERT.mockReset();
    FROM.mockClear();
    UPSERT.mockResolvedValue({ error: null });
  });
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
    expect(loggerErrorMock).toHaveBeenCalledWith("persist_failed", {
      error: "boom",
      propertyId: "prop-999",
    });
  });
});
