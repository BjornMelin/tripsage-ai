/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

const getCachedJsonSafeMock = vi.hoisted(() => vi.fn());
const setCachedJsonMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/cache/upstash", () => ({
  getCachedJsonSafe: (...args: unknown[]) => getCachedJsonSafeMock(...args),
  setCachedJson: (...args: unknown[]) => setCachedJsonMock(...args),
}));

vi.mock("@/lib/cache/hash", () => ({
  hashInputForCache: () => "hashinput",
}));

vi.mock("@/lib/ratelimit/identifier", () => ({
  hashIdentifier: (value: string) => `hash:${value}`,
}));

const retrieveDocumentsMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/rag/retriever", () => ({
  retrieveDocuments: (...args: unknown[]) => retrieveDocumentsMock(...args),
}));

vi.mock("@/lib/rag/reranker", () => ({
  createReranker: () => ({ rerank: vi.fn(async () => []) }),
}));

import { handleRagSearch } from "../_handler";

function createSupabaseMock(rows: unknown[], error: { message: string } | null = null) {
  const select = vi.fn().mockReturnThis();
  const inFn = vi.fn().mockResolvedValue({ data: error ? null : rows, error });
  const from = vi.fn(() => ({ in: inFn, select }));
  return { from, inFn, select };
}

describe("handleRagSearch (cache)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getCachedJsonSafeMock.mockReset();
    setCachedJsonMock.mockReset();
    retrieveDocumentsMock.mockReset();
  });

  it("serves from cache when available and rehydrates rows from Supabase", async () => {
    getCachedJsonSafeMock.mockResolvedValueOnce({
      data: {
        rerankingApplied: true,
        results: [
          {
            chunkIndex: 0,
            combinedScore: 0.9,
            id: "00000000-0000-0000-0000-000000000001",
            keywordRank: 0.2,
            rerankScore: 0.8,
            similarity: 0.7,
          },
        ],
        total: 1,
        version: 1,
      },
      status: "hit",
    });

    const dbRows = [
      {
        chunk_index: 0,
        content: "Cached content",
        id: "00000000-0000-0000-0000-000000000001",
        metadata: { source: "seed" },
        namespace: "default",
        source_id: "fixture:hello",
      },
    ];

    const supabase = createSupabaseMock(dbRows);

    const response = await handleRagSearch(
      {
        embeddingModelId: "openai/text-embedding-3-small",
        supabase: supabase as never,
        userId: "user-1",
      },
      {
        keywordWeight: 0.3,
        limit: 10,
        namespace: "default",
        query: "hello",
        semanticWeight: 0.7,
        threshold: 0.7,
        useReranking: true,
      }
    );

    expect(retrieveDocumentsMock).not.toHaveBeenCalled();
    expect(supabase.from).toHaveBeenCalledWith("rag_documents");

    const json = await response.json();
    expect(json.success).toBe(true);
    expect(json.rerankingApplied).toBe(true);
    expect(json.total).toBe(1);
    expect(json.results[0].content).toBe("Cached content");
    expect(json.results[0].rerankScore).toBe(0.8);
  });

  it("computes fresh results and caches a content-free entry on miss", async () => {
    getCachedJsonSafeMock.mockResolvedValueOnce({ status: "miss" });
    retrieveDocumentsMock.mockResolvedValueOnce({
      latencyMs: 12,
      query: "hello",
      rerankingApplied: false,
      results: [
        {
          chunkIndex: 0,
          combinedScore: 0.5,
          content: "Fresh content",
          id: "00000000-0000-0000-0000-000000000002",
          keywordRank: 0.1,
          metadata: {},
          namespace: "default",
          similarity: 0.5,
          sourceId: null,
        },
      ],
      success: true,
      total: 1,
    });

    const supabase = createSupabaseMock([]);

    const response = await handleRagSearch(
      {
        embeddingModelId: "openai/text-embedding-3-small",
        supabase: supabase as never,
        userId: "user-1",
      },
      {
        keywordWeight: 0.3,
        limit: 10,
        namespace: "default",
        query: "hello",
        semanticWeight: 0.7,
        threshold: 0.7,
        useReranking: false,
      }
    );

    expect(retrieveDocumentsMock).toHaveBeenCalledTimes(1);
    expect(setCachedJsonMock).toHaveBeenCalledTimes(1);

    const [, cacheValue] = setCachedJsonMock.mock.calls[0] ?? [];
    expect(cacheValue).toEqual(
      expect.objectContaining({
        rerankingApplied: false,
        version: 1,
      })
    );
    expect(cacheValue.results[0]).not.toHaveProperty("content");

    const json = await response.json();
    expect(json.success).toBe(true);
    expect(json.results[0].content).toBe("Fresh content");
  });

  it("serves cached empty results without rehydration", async () => {
    getCachedJsonSafeMock.mockResolvedValueOnce({
      data: {
        rerankingApplied: false,
        results: [],
        total: 0,
        version: 1,
      },
      status: "hit",
    });

    const supabase = createSupabaseMock([]);

    const response = await handleRagSearch(
      {
        embeddingModelId: "openai/text-embedding-3-small",
        supabase: supabase as never,
        userId: "user-1",
      },
      {
        keywordWeight: 0.3,
        limit: 10,
        namespace: "default",
        query: "nope",
        semanticWeight: 0.7,
        threshold: 0.7,
        useReranking: false,
      }
    );

    expect(retrieveDocumentsMock).not.toHaveBeenCalled();
    expect(supabase.from).not.toHaveBeenCalled();

    const json = await response.json();
    expect(json.success).toBe(true);
    expect(json.results).toEqual([]);
    expect(json.total).toBe(0);
  });
});
