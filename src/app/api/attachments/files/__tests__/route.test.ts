/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  getApiRouteSupabaseMock,
  mockApiRouteAuthUser,
  resetApiRouteMocks,
} from "@/test/helpers/api-route";
import { createRouteParamsContext } from "@/test/helpers/route";

// Mock cache functions to skip caching in tests
vi.mock("@/lib/cache/upstash", () => ({
  getCachedJson: vi.fn(() => Promise.resolve(null)),
  setCachedJson: vi.fn(() => Promise.resolve()),
}));

describe("/api/attachments/files", () => {
  // Storage mock for signed URL generation
  const mockCreateSignedUrls = vi.fn();

  beforeEach(() => {
    resetApiRouteMocks();
    mockApiRouteAuthUser({ id: "user-1" });
    vi.clearAllMocks();

    // Setup storage mock for signed URL generation
    const supabase = getApiRouteSupabaseMock();
    // biome-ignore lint/suspicious/noExplicitAny: test mock
    (supabase.storage as any) = {
      from: vi.fn(() => ({
        createSignedUrls: mockCreateSignedUrls,
      })),
    };

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

  /**
   * Helper to setup Supabase query chain mock.
   * @param supabase - Supabase client mock
   * @param options - Mock response options (count, data, error)
   * @returns Object with all mock functions for assertions
   */
  function setupSupabaseQueryMock(
    supabase: ReturnType<typeof getApiRouteSupabaseMock>,
    options: { count: number | null; data: unknown[] | null; error: unknown }
  ) {
    const rangeMock = vi.fn().mockResolvedValue(options);
    const orderMock = vi.fn(() => ({ range: rangeMock }));
    const eqMock = vi.fn(() => ({ order: orderMock }));
    const selectMock = vi.fn(() => ({ eq: eqMock }));
    // biome-ignore lint/suspicious/noExplicitAny: test mock
    (supabase.from as any) = vi.fn(() => ({ select: selectMock }));

    return { eqMock, orderMock, rangeMock, selectMock };
  }

  it("should list attachments from Supabase", async () => {
    // Mock Supabase query chain
    const supabase = getApiRouteSupabaseMock();
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

    const { eqMock, selectMock } = setupSupabaseQueryMock(supabase, {
      count: 1,
      data: mockAttachments,
      error: null,
    });

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
    expect(selectMock).toHaveBeenCalledWith("*", { count: "exact" });
    expect(eqMock).toHaveBeenCalledWith("user_id", "user-1");

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

    setupSupabaseQueryMock(supabase, {
      count: 30, // Total 30 items
      data: mockAttachments, // Return 20 items for this page
      error: null,
    });

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

    // Create a chainable query builder mock
    const eqMock = vi.fn();
    const orderMock = vi.fn();
    const rangeMock = vi.fn();
    const selectMock = vi.fn();

    // Each method returns the chainable object (including then for Promise-like behavior)
    const chainable = {
      eq: eqMock,
      order: orderMock,
      range: rangeMock,
      // biome-ignore lint/suspicious/noThenProperty: Required for Promise-like Supabase query mock
      then: (
        resolve: (value: { count: number; data: unknown[]; error: null }) => void
      ) => {
        resolve({ count: 0, data: [], error: null });
      },
    };

    eqMock.mockReturnValue(chainable);
    orderMock.mockReturnValue(chainable);
    rangeMock.mockReturnValue(chainable);
    selectMock.mockReturnValue(chainable);

    // biome-ignore lint/suspicious/noExplicitAny: test mock
    (supabase.from as any) = vi.fn(() => ({ select: selectMock }));

    const mod = await import("../route");
    const req = new NextRequest("http://localhost/api/attachments/files?tripId=123", {
      method: "GET",
    });

    const res = await mod.GET(req, createRouteParamsContext());
    expect(res.status).toBe(200);

    // Verify tripId filter was applied (as number after coercion)
    expect(eqMock).toHaveBeenCalledWith("user_id", "user-1");
    expect(eqMock).toHaveBeenCalledWith("trip_id", 123);
  });

  it("should filter by chatMessageId when provided", async () => {
    const supabase = getApiRouteSupabaseMock();

    // Create a chainable query builder mock
    const eqMock = vi.fn();
    const orderMock = vi.fn();
    const rangeMock = vi.fn();
    const selectMock = vi.fn();

    // Each method returns the chainable object (including then for Promise-like behavior)
    const chainable = {
      eq: eqMock,
      order: orderMock,
      range: rangeMock,
      // biome-ignore lint/suspicious/noThenProperty: Required for Promise-like Supabase query mock
      then: (
        resolve: (value: { count: number; data: unknown[]; error: null }) => void
      ) => {
        resolve({ count: 0, data: [], error: null });
      },
    };

    eqMock.mockReturnValue(chainable);
    orderMock.mockReturnValue(chainable);
    rangeMock.mockReturnValue(chainable);
    selectMock.mockReturnValue(chainable);

    // biome-ignore lint/suspicious/noExplicitAny: test mock
    (supabase.from as any) = vi.fn(() => ({ select: selectMock }));

    const mod = await import("../route");
    const req = new NextRequest(
      "http://localhost/api/attachments/files?chatMessageId=456",
      { method: "GET" }
    );

    const res = await mod.GET(req, createRouteParamsContext());
    expect(res.status).toBe(200);

    // Verify chatMessageId filter was applied (as number after coercion)
    expect(eqMock).toHaveBeenCalledWith("user_id", "user-1");
    expect(eqMock).toHaveBeenCalledWith("chat_message_id", 456);
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

    const rangeMock = vi.fn().mockResolvedValue({
      count: null,
      data: null,
      error: { message: "Database connection failed" },
    });
    const orderMock = vi.fn(() => ({ range: rangeMock }));
    const eqMock = vi.fn(() => ({ order: orderMock }));
    const selectMock = vi.fn(() => ({ eq: eqMock }));
    // biome-ignore lint/suspicious/noExplicitAny: test mock
    (supabase.from as any) = vi.fn(() => ({ select: selectMock }));

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

    const rangeMock = vi.fn().mockResolvedValue({
      count: 0,
      data: [],
      error: null,
    });
    const orderMock = vi.fn(() => ({ range: rangeMock }));
    const eqMock = vi.fn(() => ({ order: orderMock }));
    const selectMock = vi.fn(() => ({ eq: eqMock }));
    // biome-ignore lint/suspicious/noExplicitAny: test mock
    (supabase.from as any) = vi.fn(() => ({ select: selectMock }));

    const mod = await import("../route");
    // No limit or offset provided
    const req = new NextRequest("http://localhost/api/attachments/files", {
      method: "GET",
    });

    const res = await mod.GET(req, createRouteParamsContext());
    expect(res.status).toBe(200);

    // Default pagination: offset=0, limit=20
    expect(rangeMock).toHaveBeenCalledWith(0, 19);

    const body = await res.json();
    expect(body.pagination.limit).toBe(20);
    expect(body.pagination.offset).toBe(0);
  });

  it("should handle empty results gracefully", async () => {
    const supabase = getApiRouteSupabaseMock();

    const rangeMock = vi.fn().mockResolvedValue({
      count: 0,
      data: [],
      error: null,
    });
    const orderMock = vi.fn(() => ({ range: rangeMock }));
    const eqMock = vi.fn(() => ({ order: orderMock }));
    const selectMock = vi.fn(() => ({ eq: eqMock }));
    // biome-ignore lint/suspicious/noExplicitAny: test mock
    (supabase.from as any) = vi.fn(() => ({ select: selectMock }));

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

  it("should handle signed URL generation failure gracefully", async () => {
    const supabase = getApiRouteSupabaseMock();
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

    const rangeMock = vi.fn().mockResolvedValue({
      count: 1,
      data: mockAttachments,
      error: null,
    });
    const orderMock = vi.fn(() => ({ range: rangeMock }));
    const eqMock = vi.fn(() => ({ order: orderMock }));
    const selectMock = vi.fn(() => ({ eq: eqMock }));
    // biome-ignore lint/suspicious/noExplicitAny: test mock
    (supabase.from as any) = vi.fn(() => ({ select: selectMock }));

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
    // URL should be null when signed URL generation fails
    expect(body.items[0].url).toBeNull();
  });
});
