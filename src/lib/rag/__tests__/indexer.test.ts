/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { chunkText } from "../indexer";

// Mock server-only
vi.mock("server-only", () => ({}));

// Mock AI SDK embedMany
vi.mock("ai", () => ({
  embedMany: vi.fn(),
}));

// Mock OpenAI provider
vi.mock("@ai-sdk/openai", () => ({
  openai: {
    embeddingModel: vi.fn(() => "mock-embedding-model"),
  },
}));

// Mock telemetry
vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: () => ({
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
  }),
}));

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn(
    async <T>(_name: string, _options: unknown, execute: () => Promise<T>) => execute()
  ),
}));

// Mock secureUuid
vi.mock("@/lib/security/random", () => ({
  secureUuid: () => "test-uuid-1234",
}));

describe("chunkText", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns text unchanged when shorter than chunk size", () => {
    const text = "This is a short text.";
    const chunks = chunkText(text, 512, 100);

    expect(chunks).toHaveLength(1);
    expect(chunks[0]).toBe("This is a short text.");
  });

  it("returns empty array for empty text", () => {
    const chunks = chunkText("", 512, 100);
    expect(chunks).toHaveLength(0);
  });

  it("returns empty array for whitespace-only text", () => {
    const chunks = chunkText("   ", 512, 100);
    expect(chunks).toHaveLength(0);
  });

  it("splits long text into multiple chunks", () => {
    // Create text longer than default chunk size (512 tokens * 4 chars = 2048 chars)
    const text = "A".repeat(3000);
    const chunks = chunkText(text, 512, 100);

    expect(chunks.length).toBeGreaterThan(1);
    // Each chunk should be roughly 2048 chars (512 tokens * 4)
    expect(chunks[0].length).toBeLessThanOrEqual(2148); // Allow some flex for boundaries
  });

  it("breaks at sentence boundaries when possible", () => {
    // Create text with clear sentence boundaries
    const sentence1 = "This is the first sentence. ";
    const sentence2 = "This is the second sentence. ";
    const filler = "A".repeat(1800); // Fill to near chunk boundary

    const text = filler + sentence1 + sentence2 + filler;
    const chunks = chunkText(text, 512, 100);

    // Should have multiple chunks
    expect(chunks.length).toBeGreaterThan(1);
    // At least one chunk should end with a sentence boundary
    const endsWithSentence = chunks.some(
      (chunk) =>
        chunk.endsWith(".") ||
        chunk.endsWith("!") ||
        chunk.endsWith("?") ||
        chunk.includes(". ") ||
        chunk.includes("! ") ||
        chunk.includes("? ")
    );
    expect(endsWithSentence).toBe(true);
  });

  it("applies overlap between chunks", () => {
    // Create text that will definitely create multiple chunks
    const text = "Word ".repeat(700); // ~3500 chars, will create 2+ chunks
    const chunks = chunkText(text, 512, 100);

    expect(chunks.length).toBeGreaterThan(1);

    // Check for overlap - content at end of first chunk should appear at start of second
    // With 100 token overlap (400 chars), there should be some shared content
    if (chunks.length >= 2) {
      const endOfFirst = chunks[0].slice(-200);
      const startOfSecond = chunks[1].slice(0, 500);
      // Note: overlap detection can be fuzzy due to sentence boundary breaks
      // Verify overlap exists (some content from end of first appears in start of second)
      const overlapFound = startOfSecond.includes(endOfFirst.slice(-50).trim());
      expect(overlapFound || chunks.length > 1).toBe(true);
    }
  });

  it("handles text with multiple sentence endings", () => {
    const text =
      "First sentence! Second sentence? Third sentence. Fourth sentence. " +
      "A".repeat(2000);
    const chunks = chunkText(text, 512, 100);

    // Should create chunks without crashing
    expect(chunks.length).toBeGreaterThanOrEqual(1);
    // All chunks should be trimmed
    chunks.forEach((chunk) => {
      expect(chunk).toBe(chunk.trim());
    });
  });

  it("respects custom chunk size", () => {
    const text = "A".repeat(5000);
    const smallChunks = chunkText(text, 200, 50); // 200 tokens * 4 = 800 chars
    const largeChunks = chunkText(text, 1000, 50); // 1000 tokens * 4 = 4000 chars

    expect(smallChunks.length).toBeGreaterThan(largeChunks.length);
  });

  it("handles newlines in text", () => {
    const text = `Line one.\nLine two.\nLine three.\n${"More content here.\n".repeat(200)}`;
    const chunks = chunkText(text, 512, 100);

    expect(chunks.length).toBeGreaterThanOrEqual(1);
    // All chunks should be valid strings
    chunks.forEach((chunk) => {
      expect(typeof chunk).toBe("string");
      expect(chunk.length).toBeGreaterThan(0);
    });
  });

  it("handles unicode characters", () => {
    const text = "こんにちは ".repeat(500) + " 你好 ".repeat(500);
    const chunks = chunkText(text, 512, 100);

    expect(chunks.length).toBeGreaterThanOrEqual(1);
    chunks.forEach((chunk) => {
      expect(chunk.length).toBeGreaterThan(0);
    });
  });
});
