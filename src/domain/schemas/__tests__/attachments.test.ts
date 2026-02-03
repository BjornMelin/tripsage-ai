import { describe, expect, it } from "vitest";
import { attachmentFileSchema } from "../attachments";

describe("attachmentFileSchema", () => {
  it("accepts ISO datetimes for createdAt/updatedAt", () => {
    const parsed = attachmentFileSchema.safeParse({
      chatId: null,
      chatMessageId: 123,
      createdAt: "2026-01-01T12:34:56.789Z",
      id: "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      mimeType: "text/plain",
      name: "notes.txt",
      originalName: "notes.txt",
      size: 10,
      tripId: 42,
      updatedAt: "2026-01-01T12:34:56.789Z",
      uploadStatus: "completed",
      url: "https://example.com/notes.txt",
    });

    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.createdAt).toBe("2026-01-01T12:34:56.789Z");
      expect(parsed.data.updatedAt).toBe("2026-01-01T12:34:56.789Z");
    }
  });

  it("rejects non-ISO datetimes for createdAt/updatedAt", () => {
    const parsed = attachmentFileSchema.safeParse({
      chatId: null,
      chatMessageId: 123,
      createdAt: "2026-01-01 12:34:56",
      id: "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      mimeType: "text/plain",
      name: "notes.txt",
      originalName: "notes.txt",
      size: 10,
      tripId: 42,
      updatedAt: "2026-01-01 12:34:56",
      uploadStatus: "completed",
      url: "https://example.com/notes.txt",
    });

    expect(parsed.success).toBe(false);
  });
});
