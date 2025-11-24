/** @vitest-environment node */

import { HttpResponse, http } from "msw";
import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { mockApiRouteAuthUser, resetApiRouteMocks } from "@/test/api-route-helpers";
import { server } from "@/test/msw/server";
import { createMockNextRequest, createRouteParamsContext } from "@/test/route-helpers";

describe("/api/chat/attachments", () => {
  beforeEach(() => {
    resetApiRouteMocks();
    mockApiRouteAuthUser({ id: "user-1" });
    vi.clearAllMocks();
    server.resetHandlers();
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
    expect(body.message).toBe("Invalid content type");
    expect(body.code).toBe("INVALID_CONTENT_TYPE");
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
    expect(body.message).toBe("No files uploaded");
    expect(body.code).toBe("NO_FILES");
  });

  it("should handle valid single file upload", async () => {
    server.use(
      http.post("http://localhost:8001/api/attachments/upload", async ({ request }) => {
        const body = await request.formData();
        expect(body.get("file")).toBeInstanceOf(File);
        return HttpResponse.json(
          {
            file_id: "test-uuid-1234",
            file_size: 1000,
            filename: "test.jpg",
            mime_type: "image/jpeg",
            processing_status: "completed",
          },
          { status: 200 }
        );
      })
    );

    const mod = await import("../route");
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
  });

  it("should handle multiple file upload", async () => {
    server.use(
      http.post(
        "http://localhost:8001/api/attachments/upload/batch",
        async ({ request }) => {
          const body = await request.formData();
          const files = body.getAll("files");
          expect(files).toHaveLength(2);
          return HttpResponse.json({
            successful_uploads: [
              {
                fileId: "test-uuid-1",
                filename: "file1.png",
                fileSize: 100,
                mimeType: "image/png",
                processingStatus: "completed",
              },
              {
                fileId: "test-uuid-2",
                filename: "file2.pdf",
                fileSize: 200,
                mimeType: "application/pdf",
                processingStatus: "completed",
              },
            ],
          });
        }
      )
    );

    const mod = await import("../route");
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
    expect(body.message).toContain("exceeds maximum size");
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
    expect(body.message).toContain("Maximum 5 files allowed");
    expect(body.code).toBe("TOO_MANY_FILES");
  });

  it("should handle backend errors", async () => {
    server.use(
      http.post("http://localhost:8001/api/attachments/upload", () =>
        HttpResponse.json({ detail: "Backend error" }, { status: 500 })
      )
    );
    const mod = await import("../route");

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
    expect(body.message).toBe("Backend error");
    expect(body.code).toBe("UPLOAD_ERROR");
  });

  it("should handle network errors", async () => {
    server.use(
      http.post("http://localhost:8001/api/attachments/upload", () => {
        return HttpResponse.error();
      })
    );
    const mod = await import("../route");
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
    expect(body.error).toBe("internal");
    expect(body.reason).toBe("Internal server error");
  });

  it("should include authorization header when provided", async () => {
    let capturedAuth: string | null = null;
    server.use(
      http.post("http://localhost:8001/api/attachments/upload", ({ request }) => {
        capturedAuth = request.headers.get("authorization");
        return HttpResponse.json({
          file_id: "test-uuid-1234",
          file_size: 1000,
          filename: "test.jpg",
          mime_type: "image/jpeg",
          processing_status: "completed",
        });
      })
    );
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
    expect(capturedAuth).toBe("Bearer token123");
  });
});
