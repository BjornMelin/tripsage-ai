import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { POST } from "../route";

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("/api/chat/attachments route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          file_id: "test-uuid-1234",
          filename: "test.jpg",
          file_size: 1000,
          mime_type: "image/jpeg",
          processing_status: "completed",
        }),
        { status: 200 }
      )
    );
  });

  it("should validate content type header", async () => {
    const mockRequest = {
      headers: {
        get: vi.fn().mockReturnValue("application/json"),
      },
    } as unknown as NextRequest;

    const response = await POST(mockRequest);

    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.error).toBe("Invalid content type");
    expect(body.code).toBe("INVALID_CONTENT_TYPE");
  });

  it("should reject empty form data", async () => {
    const mockRequest = {
      headers: {
        get: vi.fn().mockReturnValue("multipart/form-data; boundary=test"),
      },
      formData: vi.fn().mockResolvedValue({
        values: () => [],
      }),
    } as unknown as NextRequest;

    const response = await POST(mockRequest);

    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.error).toBe("No files uploaded");
    expect(body.code).toBe("NO_FILES");
  });

  it("should handle valid single file upload", async () => {
    // Create a real File object for better instanceof check
    const validFile = new File(["test content"], "test.jpg", { type: "image/jpeg" });

    const mockRequest = {
      headers: {
        get: vi.fn((key) => {
          if (key === "content-type") return "multipart/form-data; boundary=test";
          if (key === "authorization") return null;
          return null;
        }),
      },
      formData: vi.fn().mockResolvedValue({
        values: () => [validFile],
      }),
    } as unknown as NextRequest;

    const response = await POST(mockRequest);

    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.files).toHaveLength(1);
    expect(body.files[0]).toMatchObject({
      id: "test-uuid-1234",
      name: "test.jpg",
      size: 1000,
      type: "image/jpeg",
      status: "completed",
    });
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8001/api/attachments/upload",
      expect.objectContaining({
        method: "POST",
      })
    );
  });

  it("should handle multiple file upload", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          successful_uploads: [
            {
              file_id: "test-uuid-1",
              filename: "file1.png",
              file_size: 100,
              mime_type: "image/png",
              processing_status: "completed",
            },
            {
              file_id: "test-uuid-2",
              filename: "file2.pdf",
              file_size: 200,
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

    const mockRequest = {
      headers: {
        get: vi.fn((key) => {
          if (key === "content-type") return "multipart/form-data; boundary=test";
          if (key === "authorization") return null;
          return null;
        }),
      },
      formData: vi.fn().mockResolvedValue({
        values: () => [file1, file2],
      }),
    } as unknown as NextRequest;

    const response = await POST(mockRequest);

    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.files).toHaveLength(2);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8001/api/attachments/upload/batch",
      expect.objectContaining({
        method: "POST",
      })
    );
  });

  it("should reject files exceeding size limit", async () => {
    // Create a file with large size
    const largeFile = new File(["content"], "large.jpg", { type: "image/jpeg" });
    Object.defineProperty(largeFile, "size", {
      value: 11 * 1024 * 1024, // 11MB
      writable: false,
    });

    const mockRequest = {
      headers: {
        get: vi.fn().mockReturnValue("multipart/form-data; boundary=test"),
      },
      formData: vi.fn().mockResolvedValue({
        values: () => [largeFile],
      }),
    } as unknown as NextRequest;

    const response = await POST(mockRequest);

    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.error).toContain("exceeds maximum size");
    expect(body.code).toBe("FILE_TOO_LARGE");
  });

  it("should reject more than 5 files", async () => {
    const files = Array.from(
      { length: 6 },
      (_, i) => new File(["content"], `file${i}.txt`, { type: "text/plain" })
    );

    const mockRequest = {
      headers: {
        get: vi.fn().mockReturnValue("multipart/form-data; boundary=test"),
      },
      formData: vi.fn().mockResolvedValue({
        values: () => files,
      }),
    } as unknown as NextRequest;

    const response = await POST(mockRequest);

    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.error).toContain("Maximum 5 files allowed");
    expect(body.code).toBe("TOO_MANY_FILES");
  });

  it("should handle backend errors", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Backend error" }), { status: 500 })
    );

    const validFile = new File(["content"], "test.jpg", { type: "image/jpeg" });

    const mockRequest = {
      headers: {
        get: vi.fn((key) => {
          if (key === "content-type") return "multipart/form-data; boundary=test";
          if (key === "authorization") return null;
          return null;
        }),
      },
      formData: vi.fn().mockResolvedValue({
        values: () => [validFile],
      }),
    } as unknown as NextRequest;

    const response = await POST(mockRequest);

    expect(response.status).toBe(500);
    const body = await response.json();
    expect(body.error).toBe("Backend error");
    expect(body.code).toBe("UPLOAD_ERROR");
  });

  it("should handle network errors", async () => {
    mockFetch.mockRejectedValueOnce(new Error("Network error"));

    const validFile = new File(["content"], "test.jpg", { type: "image/jpeg" });

    const mockRequest = {
      headers: {
        get: vi.fn((key) => {
          if (key === "content-type") return "multipart/form-data; boundary=test";
          if (key === "authorization") return null;
          return null;
        }),
      },
      formData: vi.fn().mockResolvedValue({
        values: () => [validFile],
      }),
    } as unknown as NextRequest;

    const response = await POST(mockRequest);

    expect(response.status).toBe(500);
    const body = await response.json();
    expect(body.error).toBe("Internal server error");
    expect(body.code).toBe("INTERNAL_ERROR");
  });

  it("should include authorization header when provided", async () => {
    const validFile = new File(["content"], "test.jpg", { type: "image/jpeg" });

    const mockRequest = {
      headers: {
        get: vi.fn((key) => {
          if (key === "content-type") return "multipart/form-data; boundary=test";
          if (key === "authorization") return "Bearer token123";
          return null;
        }),
      },
      formData: vi.fn().mockResolvedValue({
        values: () => [validFile],
      }),
    } as unknown as NextRequest;

    await POST(mockRequest);

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8001/api/attachments/upload",
      expect.objectContaining({
        method: "POST",
        headers: { Authorization: "Bearer token123" },
      })
    );
  });
});
