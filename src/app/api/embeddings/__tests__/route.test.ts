/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as route from "@/app/api/embeddings/route";
import { setRateLimitFactoryForTests } from "@/lib/api/factory";
import { __resetServerEnvCacheForTest } from "@/lib/env/server";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/helpers/route";

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
vi.mock("@/lib/api/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/route-helpers")>(
    "@/lib/api/route-helpers"
  );
  return {
    ...actual,
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});

vi.mock("ai", () => ({
  embed: vi.fn(async () => ({
    embedding: Array.from({ length: 1536 }, (_, i) => i / 1536),
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
    vi.stubEnv("EMBEDDINGS_API_KEY", "test-embeddings-key-1234567890");
    __resetServerEnvCacheForTest();
    setRateLimitFactoryForTests(async () => ({
      limit: 60,
      remaining: 59,
      reset: Date.now() + 60_000,
      success: true,
    }));
  });

  afterEach(() => {
    setRateLimitFactoryForTests(null);
    vi.unstubAllEnvs();
    __resetServerEnvCacheForTest();
  });

  it("returns 503 when embeddings are disabled (missing key)", async () => {
    vi.stubEnv("EMBEDDINGS_API_KEY", "");
    __resetServerEnvCacheForTest();

    const res = await route.POST(
      createMockNextRequest({
        body: { text: "hello world" },
        method: "POST",
        url: "http://localhost/api/embeddings",
      }),
      createRouteParamsContext()
    );
    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.error).toBe("embeddings_disabled");
  });

  it("returns 401 when internal key is missing", async () => {
    const res = await route.POST(
      createMockNextRequest({
        body: { text: "hello world" },
        headers: { "x-internal-key": "" },
        method: "POST",
        url: "http://localhost/api/embeddings",
      }),
      createRouteParamsContext()
    );
    expect(res.status).toBe(401);
  });

  it("returns 403 when internal key is invalid", async () => {
    const res = await route.POST(
      createMockNextRequest({
        body: { text: "hello world" },
        headers: { "x-internal-key": "wrong" },
        method: "POST",
        url: "http://localhost/api/embeddings",
      }),
      createRouteParamsContext()
    );
    expect(res.status).toBe(403);
  });

  it("returns 400 on missing input", async () => {
    const res = await route.POST(
      createMockNextRequest({
        body: { text: "" },
        headers: { "x-internal-key": "test-embeddings-key-1234567890" },
        method: "POST",
        url: "http://localhost/api/embeddings",
      }),
      createRouteParamsContext()
    );
    expect(res.status).toBe(400);
  });

  it("returns 1536-d embedding", async () => {
    const res = await route.POST(
      createMockNextRequest({
        body: { text: "hello world" },
        headers: { "x-internal-key": "test-embeddings-key-1234567890" },
        method: "POST",
        url: "http://localhost/api/embeddings",
      }),
      createRouteParamsContext()
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
        headers: { "x-internal-key": "test-embeddings-key-1234567890" },
        method: "POST",
        url: "http://localhost/api/embeddings",
      }),
      createRouteParamsContext()
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
        headers: { "x-internal-key": "test-embeddings-key-1234567890" },
        method: "POST",
        url: "http://localhost/api/embeddings",
      }),
      createRouteParamsContext()
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
