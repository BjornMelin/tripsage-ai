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

// Mock file-type for magic byte verification
vi.mock("file-type", () => ({
  fileTypeFromBuffer: vi.fn(() => Promise.resolve({ ext: "jpg", mime: "image/jpeg" })),
}));

vi.mock("botid/server", async () => {
  const { mockBotIdHumanResponse } = await import("@/test/mocks/botid");
  return {
    checkBotId: vi.fn(async () => mockBotIdHumanResponse),
  };
});

// Mock secureUuid to return predictable values
let uuidCounter = 0;
vi.mock("@/lib/security/random", () => ({
  secureUuid: () => {
    uuidCounter++;
    return `test-uuid-${uuidCounter}`;
  },
}));

// Mock cache functions
vi.mock("next/cache", () => ({
  revalidateTag: vi.fn(),
}));

vi.mock("@/lib/cache/tags", () => ({
  bumpTag: vi.fn(() => Promise.resolve(1)),
}));

// Mock telemetry (use importOriginal to preserve sanitizeAttributes for logger)
vi.mock("@/lib/telemetry/span", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/telemetry/span")>();
  return {
    ...actual,
    recordErrorOnActiveSpan: vi.fn(),
  };
});

describe("/api/chat/attachments", () => {
  const chatId = "11111111-1111-4111-8111-111111111111";

  // Storage mock functions
  const mockUpload = vi.fn();
  const mockRemove = vi.fn();
  const mockCreateSignedUrl = vi.fn();

  beforeEach(async () => {
    resetApiRouteMocks();
    mockApiRouteAuthUser({ id: "user-1" });
    vi.clearAllMocks();
    uuidCounter = 0;

    // Reset file-type mock to return matching MIME type
    const fileType = await import("file-type");
    (fileType.fileTypeFromBuffer as ReturnType<typeof vi.fn>).mockResolvedValue({
      ext: "jpg",
      mime: "image/jpeg",
    });

    // Default mock for successful storage upload
    mockUpload.mockResolvedValue({
      data: { path: `user-1/${chatId}/test-uuid-1/test.jpg` },
      error: null,
    });
    mockRemove.mockResolvedValue({ error: null });
    mockCreateSignedUrl.mockResolvedValue({
      data: {
        signedUrl: `https://supabase.storage/signed/user-1/${chatId}/test-uuid-1/test.jpg`,
      },
      error: null,
    });

    // Setup Supabase storage mock
    const supabase = getApiRouteSupabaseMock();
    resetSupabaseMockState(supabase);

    vi.spyOn(supabase, "from");
    setupStorageFromMock(supabase, {
      createSignedUrl: mockCreateSignedUrl,
      remove: mockRemove,
      upload: mockUpload,
    });
  });

  it("should validate content type header", async () => {
    const mod = await import("../route");
    const req = new NextRequest("http://localhost/api/chat/attachments", {
      headers: { "content-type": "application/json" },
      method: "POST",
    });
    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.reason).toBe("Invalid content type");
    expect(body.error).toBe("invalid_request");
  });

  it("should reject empty form data", async () => {
    const mod = await import("../route");
    const emptyFormData = new FormData();
    emptyFormData.append("text", "not-a-file");
    const request = new Request("http://localhost/api/chat/attachments", {
      body: emptyFormData,
      method: "POST",
    });
    const req = new NextRequest(request);
    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.reason).toBe("No files uploaded");
    expect(body.error).toBe("invalid_request");
  });

  it("should upload single file to Supabase Storage", async () => {
    const supabase = getApiRouteSupabaseMock();
    const state = getSupabaseMockState(supabase);

    const mod = await import("../route");
    const validFile = new File(["test content"], "test.jpg", { type: "image/jpeg" });
    const formData = new FormData();
    formData.append("file", validFile);
    formData.append("chatId", chatId);

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: formData,
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(200);

    // Verify Supabase Storage was called
    expect(supabase.storage.from).toHaveBeenCalledWith("attachments");
    expect(mockUpload).toHaveBeenCalledTimes(1);
    expect(mockUpload).toHaveBeenCalledWith(
      expect.stringContaining(`user-1/${chatId}/`),
      expect.any(Uint8Array),
      expect.objectContaining({
        contentType: "image/jpeg",
        upsert: false,
      })
    );

    // Verify Supabase metadata insert was called (uploading -> completed)
    expect(supabase.from).toHaveBeenCalledWith("file_attachments");
    const inserts = state.insertByTable.get("file_attachments") ?? [];
    expect(inserts).toHaveLength(1);
    expect(inserts[0]).toEqual(
      expect.objectContaining({
        bucket_name: "attachments",
        chat_id: chatId,
        file_size: validFile.size,
        mime_type: "image/jpeg",
        original_filename: "test.jpg",
        upload_status: "uploading",
        user_id: "user-1",
      })
    );

    const updates = state.updateByTable.get("file_attachments") ?? [];
    expect(updates).toEqual([expect.objectContaining({ upload_status: "completed" })]);

    const body = await res.json();
    expect(body.files).toHaveLength(1);
    expect(body.files[0]).toMatchObject({
      name: "test.jpg",
      status: "completed",
      type: "image/jpeg",
    });
    expect(body.files[0].url).toContain("supabase.storage/signed");
    expect(body.urls).toHaveLength(1);
  });

  it("should upload multiple files to Supabase Storage", async () => {
    // Reset counter for predictable UUIDs
    uuidCounter = 0;

    // Clear all mocks to ensure clean state
    mockUpload.mockClear();

    // Reset file-type mock for different file types
    const fileType = await import("file-type");
    (fileType.fileTypeFromBuffer as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ ext: "png", mime: "image/png" })
      .mockResolvedValueOnce({ ext: "pdf", mime: "application/pdf" });

    const supabase = getApiRouteSupabaseMock();
    const state = getSupabaseMockState(supabase);

    // Mock multiple storage uploads
    mockUpload
      .mockResolvedValueOnce({
        data: { path: "chat/user-1/test-uuid-1-file1.png" },
        error: null,
      })
      .mockResolvedValueOnce({
        data: { path: "chat/user-1/test-uuid-3-file2.pdf" },
        error: null,
      });

    mockCreateSignedUrl
      .mockResolvedValueOnce({
        data: {
          signedUrl:
            "https://supabase.storage/signed/chat/user-1/test-uuid-1-file1.png",
        },
        error: null,
      })
      .mockResolvedValueOnce({
        data: {
          signedUrl:
            "https://supabase.storage/signed/chat/user-1/test-uuid-3-file2.pdf",
        },
        error: null,
      });

    const mod = await import("../route");
    const file1 = new File(["content1"], "file1.png", { type: "image/png" });
    const file2 = new File(["content2"], "file2.pdf", { type: "application/pdf" });
    const formData = new FormData();
    formData.append("file", file1);
    formData.append("file", file2);
    formData.append("chatId", chatId);

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: formData,
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(200);

    // Verify Supabase Storage was called twice
    expect(mockUpload).toHaveBeenCalledTimes(2);

    // Verify the response contains the expected files
    const body = await res.json();
    expect(body.files).toHaveLength(2);
    expect(body.urls).toHaveLength(2);

    const inserts = state.insertByTable.get("file_attachments") ?? [];
    expect(inserts).toHaveLength(2);
  });

  it("should reject files exceeding size limit", async () => {
    const mod = await import("../route");
    const largeContent = new Uint8Array(11 * 1024 * 1024); // 11MB
    const largeFile = new File([largeContent], "large.jpg", { type: "image/jpeg" });

    const formData = new FormData();
    formData.append("file", largeFile);

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: formData,
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.reason).toContain("exceeds maximum size");
    expect(body.error).toBe("invalid_request");

    // Verify Supabase Storage was NOT called
    expect(mockUpload).not.toHaveBeenCalled();
  });

  it("should reject more than 5 files", async () => {
    const mod = await import("../route");
    const files = Array.from(
      { length: 6 },
      (_, i) => new File(["content"], `file${i}.png`, { type: "image/png" })
    );

    const formData = new FormData();
    for (const file of files) {
      formData.append("file", file);
    }

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: formData,
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.reason).toContain("Maximum 5 files allowed");
    expect(body.error).toBe("invalid_request");

    // Verify Supabase Storage was NOT called
    expect(mockUpload).not.toHaveBeenCalled();
  });

  it("should reject unsupported MIME types", async () => {
    const mod = await import("../route");
    const executableFile = new File(["content"], "script.exe", {
      type: "application/x-msdownload",
    });

    const formData = new FormData();
    formData.append("file", executableFile);

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: formData,
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.reason).toContain("invalid type");
    expect(body.error).toBe("invalid_request");

    // Verify Supabase Storage was NOT called
    expect(mockUpload).not.toHaveBeenCalled();
  });

  it("should handle Supabase Storage upload errors", async () => {
    mockUpload.mockResolvedValueOnce({
      data: null,
      error: { message: "Storage upload failed" },
    });
    const supabase = getApiRouteSupabaseMock();
    const state = getSupabaseMockState(supabase);

    const mod = await import("../route");
    const validFile = new File(["content"], "test.jpg", { type: "image/jpeg" });
    const formData = new FormData();
    formData.append("file", validFile);
    formData.append("chatId", chatId);

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: formData,
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.reason).toBe("File upload failed");
    expect(body.error).toBe("internal");

    expect(state.insertByTable.get("file_attachments") ?? []).toHaveLength(1);
    expect(
      state.requests.some(
        (r) =>
          r.method === "DELETE" &&
          r.url.startsWith("/rest/v1/file_attachments") &&
          r.url.includes("id=eq.test-uuid-1")
      )
    ).toBe(true);
  });

  it("should handle Supabase metadata insert errors gracefully", async () => {
    const supabase = getApiRouteSupabaseMock();
    const state = getSupabaseMockState(supabase);
    state.insertErrorsByTable.set("file_attachments", { message: "Database error" });

    const mod = await import("../route");
    const validFile = new File(["content"], "test.jpg", { type: "image/jpeg" });
    const formData = new FormData();
    formData.append("file", validFile);
    formData.append("chatId", chatId);

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: formData,
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(200);

    const body = await res.json();
    // File should be marked as failed but upload still succeeds overall
    expect(body.files).toHaveLength(1);
    expect(body.files[0].status).toBe("failed");
    expect(body.files[0].url).toBeNull();

    // Storage is never touched when metadata insert fails
    expect(mockUpload).not.toHaveBeenCalled();
  });

  it("rejects payloads exceeding total size budget via content-length", async () => {
    const mod = await import("../route");
    const oversizedBytes = 60 * 1024 * 1024; // 60MB > 5 * 10MB
    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: new ReadableStream(),
      headers: {
        "content-length": String(oversizedBytes),
        "content-type": "multipart/form-data; boundary=boundary",
      },
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(413);
    const body = await res.json();
    expect(body.error).toBe("invalid_request");
  });

  it("should require authentication", async () => {
    mockApiRouteAuthUser(null);

    const mod = await import("../route");
    const validFile = new File(["content"], "test.jpg", { type: "image/jpeg" });
    const formData = new FormData();
    formData.append("file", validFile);

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: formData,
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(401);
  });

  it("should reject files with MIME type mismatch (magic byte verification)", async () => {
    // Mock file-type to return a different MIME type than declared
    const fileType = await import("file-type");
    (fileType.fileTypeFromBuffer as ReturnType<typeof vi.fn>).mockResolvedValue({
      ext: "exe",
      mime: "application/x-msdownload",
    });

    const mod = await import("../route");
    // Declare as JPEG but actually an EXE (simulated by mock)
    const disguisedFile = new File(["MZ"], "malware.jpg", { type: "image/jpeg" });
    const formData = new FormData();
    formData.append("file", disguisedFile);
    formData.append("chatId", chatId);

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: formData,
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.reason).toBe("File upload failed");
    expect(body.error).toBe("invalid_request");

    // Verify storage upload was NOT called (blocked at validation)
    expect(mockUpload).not.toHaveBeenCalled();
  });

  it("rolls back metadata when any upload in the batch fails after prior inserts", async () => {
    // First upload succeeds, second fails
    mockUpload.mockReset();
    mockUpload
      .mockResolvedValueOnce({
        data: { path: "chat/user-1/test-uuid-1-file1.png" },
        error: null,
      })
      .mockResolvedValueOnce({
        data: null,
        error: { message: "Storage upload failed" },
      });

    const fileType = await import("file-type");
    (fileType.fileTypeFromBuffer as ReturnType<typeof vi.fn>).mockResolvedValue({
      ext: "png",
      mime: "image/png",
    });

    const supabase = getApiRouteSupabaseMock();
    const state = getSupabaseMockState(supabase);
    state.insertErrorsByTable.delete("file_attachments");

    const mod = await import("../route");
    const file1 = new File(["content1"], "file1.png", { type: "image/png" });
    const file2 = new File(["content2"], "file2.png", { type: "image/png" });
    const formData = new FormData();
    formData.append("file", file1);
    formData.append("file", file2);
    formData.append("chatId", chatId);

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: formData,
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.reason).toBe("File upload failed");

    // Confirm metadata insert happened for both files (metadata-first flow)
    const inserts = state.insertByTable.get("file_attachments") ?? [];
    expect(inserts).toHaveLength(2);
    expect(inserts).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          bucket_name: "attachments",
          chat_id: chatId,
          filename: "test-uuid-1",
          id: "test-uuid-1",
          original_filename: "file1.png",
          upload_status: "uploading",
        }),
        expect.objectContaining({
          bucket_name: "attachments",
          chat_id: chatId,
          filename: "test-uuid-2",
          id: "test-uuid-2",
          original_filename: "file2.png",
          upload_status: "uploading",
        }),
      ])
    );

    // Metadata rows for successful uploads are deleted on failure
    expect(
      state.requests.some(
        (r) =>
          r.method === "DELETE" &&
          r.url.startsWith("/rest/v1/file_attachments") &&
          (r.url.includes("id=eq.test-uuid-1") || r.url.includes("id=eq.test-uuid-2"))
      )
    ).toBe(true);

    // Uploaded storage object is cleaned up
    expect(mockRemove).toHaveBeenCalledWith([`user-1/${chatId}/test-uuid-1/file1.png`]);
  });
});
