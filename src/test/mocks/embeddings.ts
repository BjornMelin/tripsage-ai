/**
 * @fileoverview Embeddings mocks for tests.
 * Use this in tests that use embedding generation.
 */

import { vi } from "vitest";

/**
 * Sets up embeddings mocks for a test file.
 * Call this at the top level of test files that use embeddings.
 *
 * @example
 * ```ts
 * import { setupEmbeddingsMocks } from "@/test/mocks/embeddings";
 * setupEmbeddingsMocks();
 * ```
 */
export function setupEmbeddingsMocks() {
  vi.mock("@/lib/embeddings/generate", () => ({
    generateEmbedding: vi.fn(async () =>
      Array.from({ length: 1536 }, (_, index) => (index + 1) / 1000)
    ),
    getEmbeddingsApiUrl: vi.fn(() => "http://localhost:3000/api/embeddings"),
    getEmbeddingsRequestHeaders: vi.fn(() => ({
      "Content-Type": "application/json",
    })),
  }));
}
