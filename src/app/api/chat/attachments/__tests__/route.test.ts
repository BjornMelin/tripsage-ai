/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  getApiRouteSupabaseMock,
  mockApiRouteAuthUser,
  resetApiRouteMocks,
} from "@/test/helpers/api-route";
import { createRouteParamsContext } from "@/test/helpers/route";
import { setupStorageFromMock } from "@/test/helpers/supabase-storage";
import { getSupabaseMockState, resetSupabaseMockState } from "@/test/mocks/supabase";

vi.mock("botid/server", async () => {
  const { mockBotIdHumanResponse } = await import("@/test/mocks/botid");
  return {
    checkBotId: vi.fn(async () => mockBotIdHumanResponse),
  };
});

let uuidCounter = 0;
vi.mock("@/lib/security/random", () => ({
  secureUuid: () => {
    uuidCounter += 1;
    return `00000000-0000-4000-8000-${String(uuidCounter).padStart(12, "0")}`;
  },
}));

vi.mock("next/cache", () => ({
  revalidateTag: vi.fn(),
}));

vi.mock("@/lib/cache/tags", () => ({
  bumpTag: vi.fn(() => Promise.resolve(1)),
}));

vi.mock("@/lib/qstash/client", () => ({
  tryEnqueueJob: vi.fn(async () => ({ success: true })),
}));

vi.mock("@/lib/telemetry/span", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/telemetry/span")>();
  return {
    ...actual,
    recordErrorOnActiveSpan: vi.fn(),
  };
});

describe("/api/chat/attachments (signed uploads)", () => {
  const userId = "11111111-1111-4111-8111-111111111111";
  const chatId = "22222222-2222-4222-8222-222222222222";

  const mockCreateSignedUploadUrl = vi.fn();

  beforeEach(() => {
    resetApiRouteMocks();
    mockApiRouteAuthUser({ id: userId });
    vi.clearAllMocks();
    uuidCounter = 0;

    mockCreateSignedUploadUrl.mockImplementation(async (path: string) => ({
      data: {
        path,
        signedUrl: `https://storage.test/signed/${encodeURIComponent(path)}`,
        token: "token-1",
      },
      error: null,
    }));

    const supabase = getApiRouteSupabaseMock();
    resetSupabaseMockState(supabase);

    setupStorageFromMock(supabase, {
      createSignedUploadUrl: mockCreateSignedUploadUrl,
    });
  });

  it("rejects requests missing chatId/tripId", async () => {
    const mod = await import("../route");

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: JSON.stringify({
        files: [{ mimeType: "application/pdf", originalName: "a.pdf", size: 10 }],
      }),
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
    const body = (await res.json()) as { error?: string; reason?: string };
    expect(body.error).toBe("invalid_request");
    expect(body.reason).toBe("Request validation failed");
  });

  it("creates signed upload URLs and persists metadata rows", async () => {
    const supabase = getApiRouteSupabaseMock();
    const state = getSupabaseMockState(supabase);
    const mod = await import("../route");

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: JSON.stringify({
        chatId,
        files: [
          { mimeType: "application/pdf", originalName: "a.pdf", size: 123 },
          { mimeType: "image/png", originalName: "b.png", size: 456 },
        ],
      }),
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(200);

    const json = (await res.json()) as { uploads?: unknown[] };
    expect(Array.isArray(json.uploads)).toBe(true);
    expect(json.uploads).toHaveLength(2);

    expect(mockCreateSignedUploadUrl).toHaveBeenCalledTimes(2);
    expect(mockCreateSignedUploadUrl).toHaveBeenCalledWith(
      expect.stringContaining(`${userId}/${chatId}/`),
      expect.objectContaining({ upsert: false })
    );

    const inserts = state.insertByTable.get("file_attachments") ?? [];
    expect(inserts).toHaveLength(2);
    expect(inserts[0]).toEqual(
      expect.objectContaining({
        bucket_name: "attachments",
        chat_id: chatId,
        original_filename: "a.pdf",
        upload_status: "uploading",
        user_id: userId,
      })
    );
  });

  it("creates trip-scoped signed upload URLs when only tripId is provided", async () => {
    const supabase = getApiRouteSupabaseMock();
    const state = getSupabaseMockState(supabase);
    const tripId = 42;
    const mod = await import("../route");

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: JSON.stringify({
        files: [{ mimeType: "application/pdf", originalName: "a.pdf", size: 123 }],
        tripId,
      }),
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(200);

    expect(mockCreateSignedUploadUrl).toHaveBeenCalledTimes(1);
    expect(mockCreateSignedUploadUrl).toHaveBeenCalledWith(
      expect.stringContaining(`${userId}/${tripId}/`),
      expect.objectContaining({ upsert: false })
    );

    const inserts = state.insertByTable.get("file_attachments") ?? [];
    expect(inserts).toHaveLength(1);
    expect(inserts[0]).toEqual(
      expect.objectContaining({
        chat_id: null,
        trip_id: tripId,
      })
    );
  });

  it("rejects disallowed mime types", async () => {
    const mod = await import("../route");

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: JSON.stringify({
        chatId,
        files: [{ mimeType: "image/svg+xml", originalName: "a.svg", size: 10 }],
      }),
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
    const body = (await res.json()) as { error?: string; reason?: string };
    expect(body.error).toBe("invalid_request");
    expect(body.reason).toBe("Request validation failed");
  });

  it("rejects requests exceeding max files", async () => {
    const mod = await import("../route");

    const files = Array.from({ length: 6 }, (_, idx) => ({
      mimeType: "application/pdf",
      originalName: `f${idx}.pdf`,
      size: 10,
    }));

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: JSON.stringify({ chatId, files }),
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
    const body = (await res.json()) as { error?: string; reason?: string };
    expect(body.error).toBe("invalid_request");
    expect(body.reason).toBe("Request validation failed");
  });

  it("returns a DB error when file_attachments insert fails", async () => {
    const supabase = getApiRouteSupabaseMock();
    const state = getSupabaseMockState(supabase);
    state.insertErrorsByTable.set("file_attachments", new Error("DB error"));
    const mod = await import("../route");

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: JSON.stringify({
        chatId,
        files: [{ mimeType: "application/pdf", originalName: "a.pdf", size: 10 }],
      }),
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(500);
    const body = (await res.json()) as { error?: string; reason?: string };
    expect(body.error).toBe("db_error");
    expect(body.reason).toBe("Failed to create attachment record");
  });

  it("returns an internal error when storage signed upload URL creation throws", async () => {
    mockCreateSignedUploadUrl.mockRejectedValueOnce(new Error("Storage unavailable"));
    const mod = await import("../route");

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: JSON.stringify({
        chatId,
        files: [{ mimeType: "application/pdf", originalName: "a.pdf", size: 10 }],
      }),
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(500);
    const body = (await res.json()) as { error?: string; reason?: string };
    expect(body.error).toBe("internal");
    expect(body.reason).toBe("Failed to create signed upload URLs");
  });

  it("handles concurrent requests without duplicate inserts", async () => {
    const supabase = getApiRouteSupabaseMock();
    const state = getSupabaseMockState(supabase);
    const mod = await import("../route");

    const makeReq = () =>
      new NextRequest("http://localhost/api/chat/attachments", {
        body: JSON.stringify({
          chatId,
          files: [
            { mimeType: "application/pdf", originalName: "a.pdf", size: 10 },
            { mimeType: "image/png", originalName: "b.png", size: 10 },
          ],
        }),
        method: "POST",
      });

    const results = await Promise.all(
      Array.from({ length: 3 }, () => mod.POST(makeReq(), createRouteParamsContext()))
    );

    for (const res of results) {
      expect(res.status).toBe(200);
    }

    const inserts = state.insertByTable.get("file_attachments") ?? [];
    expect(inserts).toHaveLength(6);
    expect(mockCreateSignedUploadUrl).toHaveBeenCalledTimes(6);

    const ids = new Set(inserts.map((row) => (row as { id?: string }).id));
    expect(ids.size).toBe(6);
  });
});
