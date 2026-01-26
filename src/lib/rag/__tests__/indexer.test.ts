/** @vitest-environment node */

import type { SupabaseClient } from "@supabase/supabase-js";
import { embedMany } from "ai";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Database } from "@/lib/supabase/database.types";
import { upsertMany } from "@/lib/supabase/typed-helpers";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { chunkText, indexDocuments } from "../indexer";

// Mock server-only
vi.mock("server-only", () => ({}));

// Mock AI SDK embedMany
vi.mock("ai", () => ({
  embedMany: vi.fn(),
}));

vi.mock("@/lib/ai/embeddings/text-embedding-model", () => ({
  getTextEmbeddingModel: () => "mock-embedding-model",
  TEXT_EMBEDDING_DIMENSIONS: 1536,
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

vi.mock("@/lib/supabase/typed-helpers", () => ({
  deleteSingle: vi.fn(),
  upsertMany: vi.fn(),
}));

// Mock secureUuid
vi.mock("@/lib/security/random", () => ({
  secureUuid: () => "0c7a8d3a-4c79-4e28-9d2c-8e6a4f5b0f4a",
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
      const endOfFirst = chunks[0].slice(-300).trim();
      const startOfSecond = chunks[1].slice(0, 600);
      // Verify overlap exists (suffix of first chunk appears in second chunk)
      const overlapProbe = endOfFirst.slice(-100);
      expect(startOfSecond.includes(overlapProbe)).toBe(true);
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

describe("indexDocuments", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("upserts chunks using (id, chunk_index) and keeps `id` stable per document", async () => {
    const supabase = unsafeCast<SupabaseClient<Database>>({});
    const upsertManyMock = vi.mocked(upsertMany);
    upsertManyMock.mockResolvedValue({ data: [], error: null });

    const content1 = "A".repeat(1200);
    const content2 = "B".repeat(1200);

    const chunks1 = chunkText(content1, 100, 20);
    const chunks2 = chunkText(content2, 100, 20);
    expect(chunks1.length).toBeGreaterThan(1);
    expect(chunks2.length).toBeGreaterThan(1);

    vi.mocked(embedMany)
      .mockResolvedValueOnce({
        embeddings: chunks1.map((_, idx) => Array(1536).fill(idx)),
        usage: { tokens: 0 },
        values: chunks1,
        warnings: [],
      })
      .mockResolvedValueOnce({
        embeddings: chunks2.map((_, idx) => Array(1536).fill(idx + 1000)),
        usage: { tokens: 0 },
        values: chunks2,
        warnings: [],
      });

    const documentId = "11111111-1111-1111-1111-111111111111";

    await indexDocuments({
      config: { chunkOverlap: 20, chunkSize: 100, namespace: "default" },
      documents: [{ content: content1, id: documentId }],
      supabase,
      userId: "22222222-2222-2222-2222-222222222222",
    });

    await indexDocuments({
      config: { chunkOverlap: 20, chunkSize: 100, namespace: "default" },
      documents: [{ content: content2, id: documentId }],
      supabase,
      userId: "22222222-2222-2222-2222-222222222222",
    });

    expect(upsertManyMock).toHaveBeenCalledTimes(2);

    for (const [callIndex, expectedChunks] of [
      [0, chunks1],
      [1, chunks2],
    ] as const) {
      const [clientArg, tableArg, rowsArg, conflictArg] =
        upsertManyMock.mock.calls[callIndex] ?? [];
      expect(clientArg).toBe(supabase);
      expect(tableArg).toBe("rag_documents");
      expect(conflictArg).toBe("id,chunk_index");

      const rows = unsafeCast<Array<Record<string, unknown>>>(rowsArg);
      expect(rows).toHaveLength(expectedChunks.length);

      for (let i = 0; i < rows.length; i++) {
        expect(rows[i]?.id).toBe(documentId);
        expect(rows[i]?.chunk_index).toBe(i);
      }
    }
  });
});
