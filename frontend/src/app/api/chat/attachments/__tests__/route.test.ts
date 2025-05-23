import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { NextRequest } from "next/server";
import { POST } from "../route";
import * as fs from "fs/promises";
import path from "path";

// Mock fs/promises
vi.mock("fs/promises", () => ({
  writeFile: vi.fn(),
  mkdir: vi.fn(),
}));

// Mock crypto for consistent UUIDs
vi.mock("crypto", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    randomUUID: vi.fn(() => "test-uuid-1234"),
  };
});

describe("/api/chat/attachments route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("POST handler", () => {
    it("should accept valid image files", async () => {
      // Arrange
      const imageContent = Buffer.from("fake-image-data");
      const imageFile = new File([imageContent], "test.jpg", {
        type: "image/jpeg",
      });

      const formData = new FormData();
      formData.append("file-0", imageFile);

      const mockRequest = new NextRequest(
        "http://localhost:3000/api/chat/attachments",
        {
          method: "POST",
          body: formData,
        }
      );

      // Act
      const response = await POST(mockRequest);

      // Assert
      expect(response.status).toBe(200);
      const body = await response.json();
      expect(body.files).toHaveLength(1);
      expect(body.files[0]).toMatchObject({
        url: "/uploads/test-uuid-1234.jpg",
        id: "test-uuid-1234",
        name: "test.jpg",
        size: imageContent.length,
        type: "image/jpeg",
      });
      expect(body.urls).toEqual(["/uploads/test-uuid-1234.jpg"]);
    });

    it("should accept multiple files", async () => {
      // Arrange
      const file1 = new File([Buffer.from("image1")], "photo1.png", {
        type: "image/png",
      });
      const file2 = new File([Buffer.from("document")], "doc.pdf", {
        type: "application/pdf",
      });

      const formData = new FormData();
      formData.append("file-0", file1);
      formData.append("file-1", file2);

      const mockRequest = new NextRequest(
        "http://localhost:3000/api/chat/attachments",
        {
          method: "POST",
          body: formData,
        }
      );

      // Act
      const response = await POST(mockRequest);

      // Assert
      expect(response.status).toBe(200);
      const body = await response.json();
      expect(body.files).toHaveLength(2);
      expect(body.urls).toHaveLength(2);
    });

    it("should reject files exceeding size limit", async () => {
      // Arrange
      const largeContent = Buffer.alloc(11 * 1024 * 1024); // 11MB
      const largeFile = new File([largeContent], "large.jpg", {
        type: "image/jpeg",
      });

      const formData = new FormData();
      formData.append("file-0", largeFile);

      const mockRequest = new NextRequest(
        "http://localhost:3000/api/chat/attachments",
        {
          method: "POST",
          body: formData,
        }
      );

      // Act
      const response = await POST(mockRequest);

      // Assert
      expect(response.status).toBe(400);
      const body = await response.json();
      expect(body.error).toBe("File validation failed");
      expect(body.code).toBe("VALIDATION_ERROR");
      expect(body.details[0]).toContain("File size must not exceed 10MB");
    });

    it("should reject unsupported file types", async () => {
      // Arrange
      const execFile = new File([Buffer.from("binary")], "malware.exe", {
        type: "application/x-executable",
      });

      const formData = new FormData();
      formData.append("file-0", execFile);

      const mockRequest = new NextRequest(
        "http://localhost:3000/api/chat/attachments",
        {
          method: "POST",
          body: formData,
        }
      );

      // Act
      const response = await POST(mockRequest);

      // Assert
      expect(response.status).toBe(400);
      const body = await response.json();
      expect(body.error).toBe("File validation failed");
      expect(body.details[0]).toContain("unsupported type");
    });

    it("should reject more than 5 files", async () => {
      // Arrange
      const formData = new FormData();
      for (let i = 0; i < 6; i++) {
        const file = new File([Buffer.from(`file${i}`)], `file${i}.txt`, {
          type: "text/plain",
        });
        formData.append(`file-${i}`, file);
      }

      const mockRequest = new NextRequest(
        "http://localhost:3000/api/chat/attachments",
        {
          method: "POST",
          body: formData,
        }
      );

      // Act
      const response = await POST(mockRequest);

      // Assert
      expect(response.status).toBe(400);
      const body = await response.json();
      expect(body.error).toBe("Maximum 5 files allowed per request");
      expect(body.code).toBe("TOO_MANY_FILES");
    });

    it("should sanitize filenames", async () => {
      // Arrange
      const file = new File(
        [Buffer.from("content")],
        "../../../etc/passwd.txt",
        {
          type: "text/plain",
        }
      );

      const formData = new FormData();
      formData.append("file-0", file);

      const mockRequest = new NextRequest(
        "http://localhost:3000/api/chat/attachments",
        {
          method: "POST",
          body: formData,
        }
      );

      // Act
      const response = await POST(mockRequest);

      // Assert
      expect(response.status).toBe(200);
      const body = await response.json();
      expect(body.files[0].name).toBe("passwd.txt");
      expect(body.files[0].url).toBe("/uploads/test-uuid-1234.txt");
    });

    it("should reject empty files", async () => {
      // Arrange
      const emptyFile = new File([], "empty.txt", {
        type: "text/plain",
      });

      const formData = new FormData();
      formData.append("file-0", emptyFile);

      const mockRequest = new NextRequest(
        "http://localhost:3000/api/chat/attachments",
        {
          method: "POST",
          body: formData,
        }
      );

      // Act
      const response = await POST(mockRequest);

      // Assert
      expect(response.status).toBe(400);
      const body = await response.json();
      expect(body.error).toBe("No files uploaded");
      expect(body.code).toBe("NO_FILES");
    });

    it("should validate content type header", async () => {
      // Arrange
      const mockRequest = new NextRequest(
        "http://localhost:3000/api/chat/attachments",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ test: "data" }),
        }
      );

      // Act
      const response = await POST(mockRequest);

      // Assert
      expect(response.status).toBe(400);
      const body = await response.json();
      expect(body.error).toBe("Invalid content type");
      expect(body.code).toBe("INVALID_CONTENT_TYPE");
    });

    it("should handle file system errors gracefully", async () => {
      // Arrange
      const file = new File([Buffer.from("content")], "test.jpg", {
        type: "image/jpeg",
      });

      const formData = new FormData();
      formData.append("file-0", file);

      const mockRequest = new NextRequest(
        "http://localhost:3000/api/chat/attachments",
        {
          method: "POST",
          body: formData,
        }
      );

      // Mock writeFile to throw error
      vi.mocked(fs.writeFile).mockRejectedValueOnce(
        new Error("Disk full")
      );

      // Act
      const response = await POST(mockRequest);

      // Assert
      expect(response.status).toBe(500);
      const body = await response.json();
      expect(body.error).toBe("Failed to process file upload");
      expect(body.code).toBe("UPLOAD_ERROR");
    });

    it("should accept all allowed file types", async () => {
      // Arrange
      const allowedFiles = [
        { name: "image.jpg", type: "image/jpeg" },
        { name: "photo.png", type: "image/png" },
        { name: "animation.gif", type: "image/gif" },
        { name: "modern.webp", type: "image/webp" },
        { name: "document.pdf", type: "application/pdf" },
        { name: "notes.txt", type: "text/plain" },
        { name: "data.csv", type: "text/csv" },
        { name: "spreadsheet.xlsx", type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
      ];

      for (const fileInfo of allowedFiles) {
        const file = new File([Buffer.from("content")], fileInfo.name, {
          type: fileInfo.type,
        });

        const formData = new FormData();
        formData.append("file-0", file);

        const mockRequest = new NextRequest(
          "http://localhost:3000/api/chat/attachments",
          {
            method: "POST",
            body: formData,
          }
        );

        // Act
        const response = await POST(mockRequest);

        // Assert
        expect(response.status).toBe(200);
        const body = await response.json();
        expect(body.files).toHaveLength(1);
        expect(body.files[0].type).toBe(fileInfo.type);
      }
    });

    it("should handle special characters in filenames", async () => {
      // Arrange
      const file = new File(
        [Buffer.from("content")],
        "my file!@#$%^&*().jpg",
        {
          type: "image/jpeg",
        }
      );

      const formData = new FormData();
      formData.append("file-0", file);

      const mockRequest = new NextRequest(
        "http://localhost:3000/api/chat/attachments",
        {
          method: "POST",
          body: formData,
        }
      );

      // Act
      const response = await POST(mockRequest);

      // Assert
      expect(response.status).toBe(200);
      const body = await response.json();
      expect(body.files[0].name).toBe("my_file________.jpg");
    });
  });
});