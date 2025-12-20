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
import { getSupabaseMockState } from "@/test/mocks/supabase";

// Mock cache functions to skip caching in tests
vi.mock("@/lib/cache/upstash", () => ({
  getCachedJson: vi.fn(() => Promise.resolve(null)),
  setCachedJson: vi.fn(() => Promise.resolve()),
}));

function hasRequest(
  requests: Array<{ method: string; url: string }>,
  method: string,
  pathPrefix: string,
  params: Record<string, string>
): boolean {
  return requests.some((r) => {
    if (r.method !== method) return false;
    if (!r.url.startsWith(pathPrefix)) return false;
    const url = new URL(r.url, "http://localhost");
    return Object.entries(params).every(
      ([key, value]) => url.searchParams.get(key) === value
    );
  });
}

describe("/api/attachments/files", () => {
  // Storage mock for signed URL generation
  const mockCreateSignedUrls = vi.fn();

  beforeEach(() => {
    vi.resetModules();
    resetApiRouteMocks();
    mockApiRouteAuthUser({ id: "user-1" });
    vi.clearAllMocks();

    // Setup storage mock for signed URL generation
    const supabase = getApiRouteSupabaseMock();
    vi.spyOn(supabase, "from");
    setupStorageFromMock(supabase, { createSignedUrls: mockCreateSignedUrls });

    // Default: return signed URLs matching file paths
    mockCreateSignedUrls.mockImplementation((paths: string[]) =>
      Promise.resolve({
        data: paths.map((path) => ({
          path,
          signedUrl: `https://supabase.storage/signed/${path}?token=abc`,
        })),
        error: null,
      })
    );
  });

  it("should list attachments from Supabase", async () => {
    // Mock Supabase query chain
    const supabase = getApiRouteSupabaseMock();
    const state = getSupabaseMockState(supabase);
    const mockAttachments = [
      {
        bucket_name: "attachments",
        chat_message_id: null,
        created_at: "2025-01-01T00:00:00Z",
        file_path: "chat/user-1/uuid-test.jpg",
        file_size: 1024,
        filename: "file-id-1",
        id: "file-id-1",
        metadata: null,
        mime_type: "image/jpeg",
        original_filename: "test.jpg",
        trip_id: null,
        updated_at: "2025-01-01T00:00:00Z",
        upload_status: "completed",
        user_id: "user-1",
      },
    ];

    state.selectResult = {
      count: 1,
      data: mockAttachments,
      error: null,
    };

    const mod = await import("../route");
    const req = new NextRequest(
      "http://localhost/api/attachments/files?limit=20&offset=0",
      {
        method: "GET",
      }
    );

    const res = await mod.GET(req, createRouteParamsContext());
    expect(res.status).toBe(200);

    // Verify Supabase was called correctly
    expect(supabase.from).toHaveBeenCalledWith("file_attachments");
    expect(
      hasRequest(state.requests, "GET", "/rest/v1/file_attachments", {
        limit: "20",
        offset: "0",
        user_id: "eq.user-1",
      })
    ).toBe(true);

    // Verify storage signed URL generation was called
    expect(supabase.storage.from).toHaveBeenCalledWith("attachments");
    expect(mockCreateSignedUrls).toHaveBeenCalledWith(
      ["chat/user-1/uuid-test.jpg"],
      3600,
      { download: true }
    );

    const body = await res.json();
    expect(body.items).toHaveLength(1);
    expect(body.items[0]).toMatchObject({
      id: "file-id-1",
      mimeType: "image/jpeg",
      name: "file-id-1",
      originalName: "test.jpg",
      size: 1024,
      uploadStatus: "completed",
    });
    // URL should be a signed URL from storage
    expect(body.items[0].url).toContain("supabase.storage/signed");
    expect(body.pagination).toMatchObject({
      hasMore: false,
      limit: 20,
      nextOffset: null,
      offset: 0,
      total: 1,
    });
  });

  it("should handle pagination correctly", async () => {
    const supabase = getApiRouteSupabaseMock();
    const state = getSupabaseMockState(supabase);

    // Create mock data with 30 items total (returned 20 per page)
    const mockAttachments = Array.from({ length: 20 }, (_, i) => ({
      bucket_name: "attachments",
      chat_message_id: null,
      created_at: "2025-01-01T00:00:00Z",
      file_path: `chat/user-1/uuid-file${i}.jpg`,
      file_size: 1024,
      filename: `file-id-${i}`,
      id: `file-id-${i}`,
      metadata: null,
      mime_type: "image/jpeg",
      original_filename: `file${i}.jpg`,
      trip_id: null,
      updated_at: "2025-01-01T00:00:00Z",
      upload_status: "completed",
      user_id: "user-1",
    }));

    state.selectResult = {
      count: 30, // Total 30 items
      data: mockAttachments, // Return 20 items for this page
      error: null,
    };

    const mod = await import("../route");
    const req = new NextRequest(
      "http://localhost/api/attachments/files?limit=20&offset=0",
      {
        method: "GET",
      }
    );

    const res = await mod.GET(req, createRouteParamsContext());
    expect(res.status).toBe(200);

    const body = await res.json();
    expect(body.items).toHaveLength(20);
    expect(body.pagination).toMatchObject({
      hasMore: true,
      limit: 20,
      nextOffset: 20,
      offset: 0,
      total: 30,
    });
  });

  it("should filter by tripId when provided", async () => {
    const supabase = getApiRouteSupabaseMock();
    const state = getSupabaseMockState(supabase);

    state.selectResult = {
      count: 0,
      data: [],
      error: null,
    };

    const mod = await import("../route");
    const req = new NextRequest("http://localhost/api/attachments/files?tripId=123", {
      method: "GET",
    });

    const res = await mod.GET(req, createRouteParamsContext());
    expect(res.status).toBe(200);

    // Verify tripId filter was applied (as number after coercion)
    expect(
      state.requests.some(
        (r) =>
          r.method === "GET" &&
          r.url.startsWith("/rest/v1/file_attachments") &&
          r.url.includes("user_id=eq.user-1") &&
          r.url.includes("trip_id=eq.123")
      )
    ).toBe(true);
  });

  it("should filter by chatMessageId when provided", async () => {
    const supabase = getApiRouteSupabaseMock();
    const state = getSupabaseMockState(supabase);

    state.selectResult = {
      count: 0,
      data: [],
      error: null,
    };

    const mod = await import("../route");
    const req = new NextRequest(
      "http://localhost/api/attachments/files?chatMessageId=456",
      { method: "GET" }
    );

    const res = await mod.GET(req, createRouteParamsContext());
    expect(res.status).toBe(200);

    // Verify chatMessageId filter was applied (as number after coercion)
    expect(
      state.requests.some(
        (r) =>
          r.method === "GET" &&
          r.url.startsWith("/rest/v1/file_attachments") &&
          r.url.includes("user_id=eq.user-1") &&
          r.url.includes("chat_message_id=eq.456")
      )
    ).toBe(true);
  });

  it("should reject invalid query parameters", async () => {
    const mod = await import("../route");
    const req = new NextRequest(
      "http://localhost/api/attachments/files?limit=-1", // Invalid negative limit
      { method: "GET" }
    );

    const res = await mod.GET(req, createRouteParamsContext());
    expect(res.status).toBe(400);

    const body = await res.json();
    expect(body.error).toBe("invalid_request");
    expect(body.reason).toContain("Invalid query parameters");
  });

  it("should handle Supabase query errors", async () => {
    const supabase = getApiRouteSupabaseMock();
    const state = getSupabaseMockState(supabase);

    state.selectResult = {
      count: null,
      data: null,
      error: { message: "Database connection failed" },
    };

    const mod = await import("../route");
    const req = new NextRequest("http://localhost/api/attachments/files", {
      method: "GET",
    });

    const res = await mod.GET(req, createRouteParamsContext());
    expect(res.status).toBe(500);

    const body = await res.json();
    expect(body.error).toBe("internal");
    expect(body.reason).toBe("Failed to fetch attachments");
  });

  it("should require authentication", async () => {
    mockApiRouteAuthUser(null);

    const mod = await import("../route");
    const req = new NextRequest("http://localhost/api/attachments/files", {
      method: "GET",
    });

    const res = await mod.GET(req, createRouteParamsContext());
    expect(res.status).toBe(401);
  });

  it("should use default pagination values", async () => {
    const supabase = getApiRouteSupabaseMock();
    const state = getSupabaseMockState(supabase);

    state.selectResult = {
      count: 0,
      data: [],
      error: null,
    };

    const mod = await import("../route");
    // No limit or offset provided
    const req = new NextRequest("http://localhost/api/attachments/files", {
      method: "GET",
    });

    const res = await mod.GET(req, createRouteParamsContext());
    expect(res.status).toBe(200);

    expect(
      state.requests.some(
        (r) =>
          r.method === "GET" &&
          r.url.startsWith("/rest/v1/file_attachments") &&
          r.url.includes("offset=0") &&
          r.url.includes("limit=20")
      )
    ).toBe(true);

    const body = await res.json();
    expect(body.pagination.limit).toBe(20);
    expect(body.pagination.offset).toBe(0);
  });

  it("should handle empty results gracefully", async () => {
    const supabase = getApiRouteSupabaseMock();
    const state = getSupabaseMockState(supabase);

    state.selectResult = {
      count: 0,
      data: [],
      error: null,
    };

    const mod = await import("../route");
    const req = new NextRequest("http://localhost/api/attachments/files", {
      method: "GET",
    });

    const res = await mod.GET(req, createRouteParamsContext());
    expect(res.status).toBe(200);

    const body = await res.json();
    expect(body.items).toHaveLength(0);
    expect(body.pagination).toMatchObject({
      hasMore: false,
      limit: 20,
      nextOffset: null,
      offset: 0,
      total: 0,
    });
  });

  it("should filter out items when signed URL generation fails completely", async () => {
    const supabase = getApiRouteSupabaseMock();
    const state = getSupabaseMockState(supabase);
    const mockAttachments = [
      {
        bucket_name: "attachments",
        chat_message_id: null,
        created_at: "2025-01-01T00:00:00Z",
        file_path: "chat/user-1/uuid-test.jpg",
        file_size: 1024,
        filename: "file-id-1",
        id: "file-id-1",
        metadata: null,
        mime_type: "image/jpeg",
        original_filename: "test.jpg",
        trip_id: null,
        updated_at: "2025-01-01T00:00:00Z",
        upload_status: "completed",
        user_id: "user-1",
      },
    ];

    state.selectResult = {
      count: 1,
      data: mockAttachments,
      error: null,
    };

    // Simulate signed URL generation failure
    mockCreateSignedUrls.mockResolvedValue({
      data: null,
      error: { message: "Storage error" },
    });

    const mod = await import("../route");
    const req = new NextRequest("http://localhost/api/attachments/files", {
      method: "GET",
    });

    const res = await mod.GET(req, createRouteParamsContext());
    expect(res.status).toBe(200);

    const body = await res.json();
    // Items without valid URLs are filtered out (schema requires url to be non-null)
    expect(body.items).toHaveLength(0);
    // Pagination total still reflects DB count for cursor math
    expect(body.pagination.total).toBe(1);
  });

  it("should filter out items when individual signed URLs fail", async () => {
    const supabase = getApiRouteSupabaseMock();
    const state = getSupabaseMockState(supabase);
    const mockAttachments = [
      {
        bucket_name: "attachments",
        chat_message_id: null,
        created_at: "2025-01-01T00:00:00Z",
        file_path: "chat/user-1/file1.jpg",
        file_size: 1024,
        filename: "file-1",
        id: "file-1",
        metadata: null,
        mime_type: "image/jpeg",
        original_filename: "file1.jpg",
        trip_id: null,
        updated_at: "2025-01-01T00:00:00Z",
        upload_status: "completed",
        user_id: "user-1",
      },
      {
        bucket_name: "attachments",
        chat_message_id: null,
        created_at: "2025-01-01T00:00:00Z",
        file_path: "chat/user-1/file2.jpg",
        file_size: 2048,
        filename: "file-2",
        id: "file-2",
        metadata: null,
        mime_type: "image/jpeg",
        original_filename: "file2.jpg",
        trip_id: null,
        updated_at: "2025-01-01T00:00:00Z",
        upload_status: "completed",
        user_id: "user-1",
      },
    ];

    state.selectResult = {
      count: 2,
      data: mockAttachments,
      error: null,
    };

    // First file gets a URL, second file fails
    mockCreateSignedUrls.mockResolvedValue({
      data: [
        {
          error: null,
          path: "chat/user-1/file1.jpg",
          signedUrl: "https://supabase.storage/signed/file1.jpg?token=abc",
        },
        {
          error: "Failed to generate URL",
          path: "chat/user-1/file2.jpg",
          signedUrl: "",
        },
      ],
      error: null,
    });

    const mod = await import("../route");
    const req = new NextRequest("http://localhost/api/attachments/files", {
      method: "GET",
    });

    const res = await mod.GET(req, createRouteParamsContext());
    expect(res.status).toBe(200);

    const body = await res.json();
    // Only the item with a valid URL is returned
    expect(body.items).toHaveLength(1);
    expect(body.items[0].id).toBe("file-1");
    expect(body.items[0].url).toContain("supabase.storage/signed");
  });
});
