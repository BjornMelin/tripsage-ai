/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

// Use vi.hoisted to create mocks before vi.mock hoisting
const mockEmbed = vi.hoisted(() => vi.fn());
const mockRerank = vi.hoisted(() => vi.fn());

// Mock server-only first
vi.mock("server-only", () => ({}));

// Mock AI SDK embed function
vi.mock("ai", () => ({
  embed: mockEmbed,
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

// Mock reranker
vi.mock("../reranker", () => {
  class NoOpReranker {
    rerank() {
      return [];
    }
  }

  return {
    createReranker: (config?: { provider?: string }) => {
      if (config?.provider === "noop") return new NoOpReranker();
      return { rerank: mockRerank };
    },
    NoOpReranker,
  };
});

// Import after mocks
import { retrieveDocuments, semanticSearch } from "../retriever";

// Create a mock 1536-dimensional embedding
function createMockEmbedding(): number[] {
  return Array(1536).fill(0.1);
}

type RetrieveSupabase = Parameters<typeof retrieveDocuments>[0]["supabase"];
type SemanticSearchSupabase = Parameters<typeof semanticSearch>[0]["supabase"];

// Mock Supabase client
function createMockSupabase(rpcResult: unknown = []): RetrieveSupabase {
  return unsafeCast<RetrieveSupabase>({
    rpc: vi.fn().mockResolvedValue({
      data: rpcResult,
      error: null,
    }),
  });
}

describe("retrieveDocuments", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockEmbed.mockResolvedValue({ embedding: createMockEmbedding() });
  });

  it("generates query embedding and calls hybrid search RPC", async () => {
    const mockData = [
      {
        chunk_index: 0,
        combined_score: 0.85,
        content: "Paris travel guide",
        id: "doc-1",
        keyword_rank: 0.7,
        metadata: { type: "guide" },
        namespace: "destinations",
        similarity: 0.9,
        source_id: "src-1",
      },
    ];

    const supabase = createMockSupabase(mockData);

    const result = await retrieveDocuments({
      config: { useReranking: false },
      query: "best hotels in Paris",
      supabase,
    });

    expect(mockEmbed).toHaveBeenCalledTimes(1);
    expect(mockEmbed).toHaveBeenCalledWith(
      expect.objectContaining({
        value: "best hotels in Paris",
      })
    );

    expect(supabase.rpc).toHaveBeenCalledWith(
      "hybrid_rag_search",
      expect.objectContaining({
        query_text: "best hotels in Paris",
      })
    );

    expect(result.success).toBe(true);
    expect(result.results).toHaveLength(1);
    expect(result.results[0].content).toBe("Paris travel guide");
    expect(result.query).toBe("best hotels in Paris");
  });

  it("applies reranking when enabled", async () => {
    const mockData = [
      {
        chunk_index: 0,
        combined_score: 0.8,
        content: "Doc 1",
        id: "1",
        keyword_rank: 0.5,
        metadata: {},
        namespace: "default",
        similarity: 0.8,
        source_id: null,
      },
      {
        chunk_index: 0,
        combined_score: 0.7,
        content: "Doc 2",
        id: "2",
        keyword_rank: 0.4,
        metadata: {},
        namespace: "default",
        similarity: 0.7,
        source_id: null,
      },
    ];

    const supabase = createMockSupabase(mockData);

    mockRerank.mockResolvedValue([
      {
        ...mockData[1],
        chunkIndex: 0,
        combinedScore: 0.7,
        keywordRank: 0.4,
        rerankScore: 0.95,
        sourceId: null,
      },
      {
        ...mockData[0],
        chunkIndex: 0,
        combinedScore: 0.8,
        keywordRank: 0.5,
        rerankScore: 0.6,
        sourceId: null,
      },
    ]);

    const result = await retrieveDocuments({
      config: { useReranking: true },
      query: "query",
      supabase,
    });

    expect(mockRerank).toHaveBeenCalled();
    expect(result.rerankingApplied).toBe(true);
  });

  it("respects namespace filter", async () => {
    const supabase = createMockSupabase([]);

    await retrieveDocuments({
      config: { namespace: "accommodations" },
      query: "query",
      supabase,
    });

    expect(supabase.rpc).toHaveBeenCalledWith(
      "hybrid_rag_search",
      expect.objectContaining({
        filter_namespace: "accommodations",
      })
    );
  });

  it("respects limit configuration", async () => {
    const supabase = createMockSupabase([]);

    await retrieveDocuments({
      config: { limit: 5, useReranking: false },
      query: "query",
      supabase,
    });

    expect(supabase.rpc).toHaveBeenCalledWith(
      "hybrid_rag_search",
      expect.objectContaining({
        match_count: 5,
      })
    );
  });

  it("doubles match_count when reranking is enabled", async () => {
    const supabase = createMockSupabase([]);
    mockRerank.mockResolvedValue([]);

    await retrieveDocuments({
      config: { limit: 10, useReranking: true },
      query: "query",
      supabase,
    });

    expect(supabase.rpc).toHaveBeenCalledWith(
      "hybrid_rag_search",
      expect.objectContaining({
        match_count: 20, // 10 * 2
      })
    );
  });

  it("respects threshold configuration", async () => {
    const supabase = createMockSupabase([]);

    await retrieveDocuments({
      config: { threshold: 0.8 },
      query: "query",
      supabase,
    });

    expect(supabase.rpc).toHaveBeenCalledWith(
      "hybrid_rag_search",
      expect.objectContaining({
        match_threshold: 0.8,
      })
    );
  });

  it("falls back gracefully when reranking fails", async () => {
    const mockData = [
      {
        chunk_index: 0,
        combined_score: 0.9,
        content: "Doc 1",
        id: "1",
        keyword_rank: 0.5,
        metadata: {},
        namespace: "default",
        similarity: 0.9,
        source_id: null,
      },
    ];

    const supabase = createMockSupabase(mockData);
    mockRerank.mockRejectedValue(new Error("Rerank failed"));

    const result = await retrieveDocuments({
      config: { useReranking: true },
      query: "query",
      supabase,
    });

    expect(result.success).toBe(true);
    expect(result.rerankingApplied).toBe(false);
    expect(result.results).toHaveLength(1);
  });

  it("throws error when embedding dimension is wrong", async () => {
    mockEmbed.mockResolvedValue({ embedding: [0.1, 0.2, 0.3] }); // Wrong size

    const supabase = createMockSupabase([]);

    await expect(
      retrieveDocuments({
        query: "query",
        supabase,
      })
    ).rejects.toThrow("Query embedding dimension mismatch");
  });

  it("throws error when RPC fails", async () => {
    const supabase = unsafeCast<RetrieveSupabase>({
      rpc: vi.fn().mockResolvedValue({
        data: null,
        error: { message: "Database error" },
      }),
    });

    await expect(
      retrieveDocuments({
        query: "query",
        supabase,
      })
    ).rejects.toThrow("Hybrid search failed: Database error");
  });

  it("tracks latency in response", async () => {
    const supabase = createMockSupabase([]);

    const result = await retrieveDocuments({
      config: { useReranking: false },
      query: "query",
      supabase,
    });

    expect(result.latencyMs).toBeGreaterThanOrEqual(0);
    expect(typeof result.latencyMs).toBe("number");
  });
});

describe("semanticSearch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockEmbed.mockResolvedValue({ embedding: createMockEmbedding() });
  });

  it("performs simple semantic search", async () => {
    const mockData = [
      {
        chunk_index: 0,
        content: "Semantic result",
        id: "doc-1",
        metadata: {},
        namespace: "default",
        similarity: 0.85,
        source_id: null,
      },
    ];

    const supabase = unsafeCast<SemanticSearchSupabase>({
      rpc: vi.fn().mockResolvedValue({
        data: mockData,
        error: null,
      }),
    });

    const result = await semanticSearch({
      query: "simple search",
      supabase,
    });

    expect(supabase.rpc).toHaveBeenCalledWith(
      "match_rag_documents",
      expect.objectContaining({
        match_count: 10,
        match_threshold: 0.7,
      })
    );

    expect(result).toHaveLength(1);
    expect(result[0].content).toBe("Semantic result");
    expect(result[0].similarity).toBe(0.85);
  });

  it("respects limit and threshold parameters", async () => {
    const supabase = unsafeCast<SemanticSearchSupabase>({
      rpc: vi.fn().mockResolvedValue({
        data: [],
        error: null,
      }),
    });

    await semanticSearch({
      limit: 5,
      query: "query",
      supabase,
      threshold: 0.9,
    });

    expect(supabase.rpc).toHaveBeenCalledWith(
      "match_rag_documents",
      expect.objectContaining({
        match_count: 5,
        match_threshold: 0.9,
      })
    );
  });

  it("filters by namespace when provided", async () => {
    const supabase = unsafeCast<SemanticSearchSupabase>({
      rpc: vi.fn().mockResolvedValue({
        data: [],
        error: null,
      }),
    });

    await semanticSearch({
      namespace: "activities",
      query: "query",
      supabase,
    });

    expect(supabase.rpc).toHaveBeenCalledWith(
      "match_rag_documents",
      expect.objectContaining({
        filter_namespace: "activities",
      })
    );
  });

  it("throws error on RPC failure", async () => {
    const supabase = unsafeCast<SemanticSearchSupabase>({
      rpc: vi.fn().mockResolvedValue({
        data: null,
        error: { message: "Search failed" },
      }),
    });

    await expect(
      semanticSearch({
        query: "query",
        supabase,
      })
    ).rejects.toThrow("Semantic search failed: Search failed");
  });
});
