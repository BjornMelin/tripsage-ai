/** @vitest-environment node */

import type { RagSearchResult } from "@schemas/rag";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Use vi.hoisted to create mock before vi.mock hoisting
const mockRerank = vi.hoisted(() => vi.fn());

// Mock server-only first
vi.mock("server-only", () => ({}));

// Mock AI SDK rerank function
vi.mock("ai", () => ({
  rerank: mockRerank,
}));

// Mock Together.ai provider
vi.mock("@ai-sdk/togetherai", () => ({
  togetherai: {
    reranking: vi.fn(() => "mock-reranking-model"),
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

// Import after mocks
import { createReranker, NoOpReranker, TogetherReranker } from "../reranker";

function createMockDocument(
  id: string,
  content: string,
  combinedScore: number
): RagSearchResult {
  return {
    chunkIndex: 0,
    combinedScore,
    content,
    id,
    keywordRank: combinedScore * 0.5,
    metadata: {},
    namespace: "default",
    similarity: combinedScore,
    sourceId: null,
  };
}

describe("TogetherReranker", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv("TOGETHER_AI_API_KEY", "together_test_key_12345678901234567890");
  });

  it("returns empty array for empty documents", async () => {
    const reranker = new TogetherReranker();
    const result = await reranker.rerank("test query", [], 10);
    expect(result).toEqual([]);
    expect(mockRerank).not.toHaveBeenCalled();
  });

  it("calls AI SDK rerank with correct parameters", async () => {
    const documents = [
      createMockDocument("1", "Paris is beautiful", 0.8),
      createMockDocument("2", "London has museums", 0.7),
    ];

    mockRerank.mockResolvedValueOnce({
      ranking: [
        { document: "Paris is beautiful", originalIndex: 0, score: 0.95 },
        { document: "London has museums", originalIndex: 1, score: 0.85 },
      ],
    });

    const reranker = new TogetherReranker({ timeout: 500 });
    const result = await reranker.rerank("best city in Europe", documents, 2);

    expect(mockRerank).toHaveBeenCalledTimes(1);
    expect(mockRerank).toHaveBeenCalledWith(
      expect.objectContaining({
        documents: ["Paris is beautiful", "London has museums"],
        query: "best city in Europe",
        topN: 2,
      })
    );

    expect(result).toHaveLength(2);
    expect(result[0].rerankScore).toBe(0.95);
    expect(result[0].id).toBe("1");
    expect(result[1].rerankScore).toBe(0.85);
    expect(result[1].id).toBe("2");
  });

  it("respects topN limit from config", async () => {
    const documents = [
      createMockDocument("1", "Doc 1", 0.9),
      createMockDocument("2", "Doc 2", 0.8),
      createMockDocument("3", "Doc 3", 0.7),
    ];

    mockRerank.mockResolvedValueOnce({
      ranking: [{ document: "Doc 1", originalIndex: 0, score: 0.95 }],
    });

    const reranker = new TogetherReranker({ topN: 1 });
    const result = await reranker.rerank("query", documents, 5);

    expect(mockRerank).toHaveBeenCalledWith(
      expect.objectContaining({
        topN: 1, // Should use min(requested topN, documents.length, config.topN)
      })
    );
    expect(result).toHaveLength(1);
  });

  it("falls back to original documents on error", async () => {
    const documents = [
      createMockDocument("1", "Doc 1", 0.9),
      createMockDocument("2", "Doc 2", 0.8),
    ];

    mockRerank.mockRejectedValueOnce(new Error("API error"));

    const reranker = new TogetherReranker();
    const result = await reranker.rerank("query", documents, 2);

    // Should return original documents sorted by combinedScore
    expect(result).toHaveLength(2);
    expect(result[0].combinedScore).toBe(0.9);
    expect(result[1].combinedScore).toBe(0.8);
  });

  it("sorts results by rerank score", async () => {
    const documents = [
      createMockDocument("1", "Low relevance", 0.9),
      createMockDocument("2", "High relevance", 0.5),
    ];

    mockRerank.mockResolvedValueOnce({
      ranking: [
        { document: "High relevance", originalIndex: 1, score: 0.99 },
        { document: "Low relevance", originalIndex: 0, score: 0.3 },
      ],
    });

    const reranker = new TogetherReranker();
    const result = await reranker.rerank("query", documents, 2);

    // First result should be the one with higher rerank score
    expect(result[0].id).toBe("2");
    expect(result[0].rerankScore).toBe(0.99);
    expect(result[1].id).toBe("1");
    expect(result[1].rerankScore).toBe(0.3);
  });
});

describe("NoOpReranker", () => {
  it("returns documents sorted by combinedScore", async () => {
    const documents = [
      createMockDocument("1", "Low score", 0.3),
      createMockDocument("2", "High score", 0.9),
      createMockDocument("3", "Mid score", 0.6),
    ];

    const reranker = new NoOpReranker();
    const result = await reranker.rerank("query", documents, 10);

    expect(result).toHaveLength(3);
    expect(result[0].combinedScore).toBe(0.9);
    expect(result[1].combinedScore).toBe(0.6);
    expect(result[2].combinedScore).toBe(0.3);
  });

  it("respects topN limit", async () => {
    const documents = [
      createMockDocument("1", "Doc 1", 0.9),
      createMockDocument("2", "Doc 2", 0.8),
      createMockDocument("3", "Doc 3", 0.7),
    ];

    const reranker = new NoOpReranker();
    const result = await reranker.rerank("query", documents, 2);

    expect(result).toHaveLength(2);
    expect(result.map((d) => d.id)).toEqual(["1", "2"]);
  });

  it("handles empty document array", async () => {
    const reranker = new NoOpReranker();
    const result = await reranker.rerank("query", [], 10);
    expect(result).toEqual([]);
  });
});

describe("createReranker", () => {
  it("creates TogetherReranker by default", () => {
    vi.stubEnv("TOGETHER_AI_API_KEY", "together_test_key_12345678901234567890");
    const reranker = createReranker();
    expect(reranker).toBeInstanceOf(TogetherReranker);
  });

  it("creates TogetherReranker with provider together", () => {
    vi.stubEnv("TOGETHER_AI_API_KEY", "together_test_key_12345678901234567890");
    const reranker = createReranker({ provider: "together" });
    expect(reranker).toBeInstanceOf(TogetherReranker);
  });

  it("creates NoOpReranker with provider noop", () => {
    const reranker = createReranker({ provider: "noop" });
    expect(reranker).toBeInstanceOf(NoOpReranker);
  });

  it("passes config to reranker", () => {
    vi.stubEnv("TOGETHER_AI_API_KEY", "together_test_key_12345678901234567890");
    const reranker = createReranker({
      provider: "together",
      timeout: 1000,
      topN: 5,
    });
    expect(reranker).toBeInstanceOf(TogetherReranker);
  });

  it("propagates factory config into effective topN", async () => {
    vi.stubEnv("TOGETHER_AI_API_KEY", "together_test_key_12345678901234567890");
    const documents = [
      createMockDocument("1", "Doc 1", 0.9),
      createMockDocument("2", "Doc 2", 0.8),
      createMockDocument("3", "Doc 3", 0.7),
    ];

    mockRerank.mockResolvedValueOnce({
      ranking: [
        { document: "Doc 1", originalIndex: 0, score: 0.9 },
        { document: "Doc 2", originalIndex: 1, score: 0.8 },
      ],
    });

    const reranker = createReranker({ provider: "together", topN: 1 });
    await reranker.rerank("query", documents, 10);

    expect(mockRerank).toHaveBeenCalledWith(
      expect.objectContaining({
        topN: 1,
      })
    );
  });
});
