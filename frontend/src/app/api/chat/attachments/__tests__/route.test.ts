/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { mockApiRouteAuthUser, resetApiRouteMocks } from "@/test/api-route-helpers";
import { createMockNextRequest, createRouteParamsContext } from "@/test/route-helpers";

// Mock global fetch
const MOCK_FETCH = vi.fn();
global.fetch = MOCK_FETCH;

describe("/api/chat/attachments", () => {
  beforeEach(() => {
    resetApiRouteMocks();
    mockApiRouteAuthUser({ id: "user-1" });
    vi.clearAllMocks();
    MOCK_FETCH.mockResolvedValue(
      new Response(
        JSON.stringify({
          file_id: "test-uuid-1234",
          file_size: 1000,
          filename: "test.jpg",
          mime_type: "image/jpeg",
          processing_status: "completed",
        }),
        { status: 200 }
      )
    );
  });

  it("should validate content type header", async () => {
    const mod = await import("../route");
    const req = createMockNextRequest({
      headers: { "content-type": "application/json" },
      method: "POST",
      url: "http://localhost/api/chat/attachments",
    });
    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toBe("Invalid content type");
    expect(body.code).toBe("INVALID_CONTENT_TYPE");
  });

  it("should reject empty form data", async () => {
    const mod = await import("../route");
    // Create a FormData with a non-file entry to ensure it's parseable
    // The route filters out non-File entries, so this should result in no files
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
    expect(body.error).toBe("No files uploaded");
    expect(body.code).toBe("NO_FILES");
  });

  it("should handle valid single file upload", async () => {
    const mod = await import("../route");
    // Create a real File object and FormData for testing
    const validFile = new File(["test content"], "test.jpg", { type: "image/jpeg" });
    const formData = new FormData();
    formData.append("file", validFile);

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: formData,
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.files).toHaveLength(1);
    expect(body.files[0]).toMatchObject({
      id: "test-uuid-1234",
      name: "test.jpg",
      size: 1000,
      status: "completed",
      type: "image/jpeg",
    });
    expect(MOCK_FETCH).toHaveBeenCalledWith(
      "http://localhost:8001/api/attachments/upload",
      expect.objectContaining({
        method: "POST",
      })
    );
  });

  it("should handle multiple file upload", async () => {
    const mod = await import("../route");
    MOCK_FETCH.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          successful_uploads: [
            {
              file_id: "test-uuid-1",
              file_size: 100,
              filename: "file1.png",
              mime_type: "image/png",
              processing_status: "completed",
            },
            {
              file_id: "test-uuid-2",
              file_size: 200,
              filename: "file2.pdf",
              mime_type: "application/pdf",
              processing_status: "completed",
            },
          ],
        }),
        { status: 200 }
      )
    );

    const file1 = new File(["content1"], "file1.png", { type: "image/png" });
    const file2 = new File(["content2"], "file2.pdf", { type: "application/pdf" });
    const formData = new FormData();
    formData.append("file", file1);
    formData.append("file", file2);

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: formData,
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.files).toHaveLength(2);
    expect(MOCK_FETCH).toHaveBeenCalledWith(
      "http://localhost:8001/api/attachments/upload/batch",
      expect.objectContaining({
        method: "POST",
      })
    );
  });

  it("should reject files exceeding size limit", async () => {
    const mod = await import("../route");
    // Create a file with large size - use a Blob with explicit size
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
    expect(body.error).toContain("exceeds maximum size");
    expect(body.code).toBe("FILE_TOO_LARGE");
  });

  it("should reject more than 5 files", async () => {
    const mod = await import("../route");
    const files = Array.from(
      { length: 6 },
      (_, i) => new File(["content"], `file${i}.txt`, { type: "text/plain" })
    );

    const formData = new FormData();
    files.forEach((file) => {
      formData.append("file", file);
    });

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: formData,
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toContain("Maximum 5 files allowed");
    expect(body.code).toBe("TOO_MANY_FILES");
  });

  it("should handle backend errors", async () => {
    const mod = await import("../route");
    MOCK_FETCH.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Backend error" }), { status: 500 })
    );

    const validFile = new File(["content"], "test.jpg", { type: "image/jpeg" });
    const formData = new FormData();
    formData.append("file", validFile);

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: formData,
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.error).toBe("Backend error");
    expect(body.code).toBe("UPLOAD_ERROR");
  });

  it("should handle network errors", async () => {
    const mod = await import("../route");
    MOCK_FETCH.mockRejectedValueOnce(new Error("Network error"));

    const validFile = new File(["content"], "test.jpg", { type: "image/jpeg" });
    const formData = new FormData();
    formData.append("file", validFile);

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: formData,
      method: "POST",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(500);
    const body = await res.json();
    // withApiGuards returns error: "internal" for caught errors
    expect(body.error).toBe("internal");
    expect(body.reason).toBe("Internal server error");
  });

  it("should include authorization header when provided", async () => {
    const mod = await import("../route");
    const validFile = new File(["content"], "test.jpg", { type: "image/jpeg" });
    const formData = new FormData();
    formData.append("file", validFile);

    const req = new NextRequest("http://localhost/api/chat/attachments", {
      body: formData,
      headers: { authorization: "Bearer token123" },
      method: "POST",
    });

    await mod.POST(req, createRouteParamsContext());

    expect(MOCK_FETCH).toHaveBeenCalledWith(
      "http://localhost:8001/api/attachments/upload",
      expect.objectContaining({
        headers: { Authorization: "Bearer token123" },
        method: "POST",
      })
    );
  });
});
