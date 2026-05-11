/** @vitest-environment node */

import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import { setupUpstashTestEnvironment } from "@/test/upstash/setup";

const {
  afterAllHook: upstashAfterAllHook,
  beforeEachHook: upstashBeforeEachHook,
  mocks: upstashMocks,
} = setupUpstashTestEnvironment();

const envStore = vi.hoisted<Record<string, string | undefined>>(() => ({
  QSTASH_CURRENT_SIGNING_KEY: "current",
  QSTASH_NEXT_SIGNING_KEY: "next",
  UPSTASH_REDIS_REST_TOKEN: "token",
  UPSTASH_REDIS_REST_URL: "https://example.upstash.local",
}));

const createAdminSupabaseMock = vi.hoisted(() => vi.fn());
const indexDocumentsMock = vi.hoisted(() => vi.fn());
const recordTelemetryEventMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/env/server", () => ({
  getServerEnvVar: (key: string) => {
    const value = envStore[key];
    if (!value) throw new Error(`Missing env ${key}`);
    return value;
  },
  getServerEnvVarWithFallback: (key: string, fallback?: string) => {
    return (envStore[key] ?? fallback) as string;
  },
}));

vi.mock("@/lib/supabase/admin", () => ({
  createAdminSupabase: () => createAdminSupabaseMock(),
}));

vi.mock("@/lib/rag/indexer", () => ({
  indexDocuments: (...args: unknown[]) => indexDocumentsMock(...args),
}));

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: (...args: unknown[]) => recordTelemetryEventMock(...args),
  sanitizeAttributes: vi.fn((attrs) => attrs),
  withTelemetrySpan: vi.fn(
    (_name: string, _opts: unknown, fn: (span: unknown) => unknown) =>
      fn({
        addEvent: vi.fn(),
        recordException: vi.fn(),
        setAttribute: vi.fn(),
        setStatus: vi.fn(),
      })
  ),
}));

function makeRequest(body: unknown, headers?: Record<string, string>): Request {
  return new Request("http://localhost/api/jobs/rag-index", {
    body: JSON.stringify(body),
    headers: {
      "Content-Type": "application/json",
      "Upstash-Message-Id": "msg-1",
      "Upstash-Signature": "sig",
      ...headers,
    },
    method: "POST",
  });
}

describe("POST /api/jobs/rag-index", () => {
  beforeEach(() => {
    upstashBeforeEachHook();
    vi.clearAllMocks();
    upstashMocks.qstash.__forceVerify(true);
    createAdminSupabaseMock.mockReset();
    recordTelemetryEventMock.mockReset();
    createAdminSupabaseMock.mockReturnValue({ from: vi.fn() });
    indexDocumentsMock.mockReset();
    indexDocumentsMock.mockResolvedValue({
      chunksCreated: 1,
      failed: [],
      indexed: 1,
      namespace: "user_content",
      success: true,
      total: 1,
    });
  });

  const loadRoute = async () => await import("../route");

  it("indexes documents successfully", async () => {
    const { POST } = await loadRoute();

    const res = await POST(
      makeRequest({
        documents: [
          {
            content: "Hello world",
            id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            metadata: { attachmentId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" },
            sourceId: "src-1",
          },
        ],
        userId: "11111111-1111-4111-8111-111111111111",
      })
    );
    const json = await res.json();

    expect(res.status).toBe(200);
    expect(json.success).toBe(true);
    expect(indexDocumentsMock).toHaveBeenCalledWith(
      expect.objectContaining({
        documents: [
          expect.objectContaining({ id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" }),
        ],
        userId: "11111111-1111-4111-8111-111111111111",
      })
    );
    expect(recordTelemetryEventMock).toHaveBeenCalledWith(
      "jobs.rag_index.completed",
      expect.objectContaining({
        attributes: expect.objectContaining({
          chunksCreated: 1,
          documentCount: 1,
          failedCount: 0,
          indexedCount: 1,
          namespace: "user_content",
          retryOutcome: "not_applicable",
        }),
      })
    );
  });

  it("returns 500 (retryable) when indexer reports partial failure", async () => {
    indexDocumentsMock.mockResolvedValue({
      chunksCreated: 1,
      failed: [{ error: "boom", index: 0 }],
      indexed: 0,
      namespace: "user_content",
      success: false,
      total: 1,
    });

    const { POST } = await loadRoute();
    const res = await POST(
      makeRequest({
        documents: [{ content: "Hello world" }],
        userId: "11111111-1111-4111-8111-111111111111",
      })
    );
    const json = await res.json();

    expect(res.status).toBe(500);
    expect(json.error).toBe("internal");
    expect(json.reason).toBe("RAG index job failed");
    expect(res.headers.get("Upstash-NonRetryable-Error")).toBeNull();
  });

  it("returns 489 when all indexer failures are non-retryable RAG budget failures", async () => {
    indexDocumentsMock.mockResolvedValue({
      chunksCreated: 0,
      failed: [{ error: "rag_limit:too_many_chunks", index: 0 }],
      indexed: 0,
      namespace: "user_content",
      success: false,
      total: 1,
    });

    const { POST } = await loadRoute();
    const res = await POST(
      makeRequest({
        documents: [{ content: "Hello world" }],
        userId: "11111111-1111-4111-8111-111111111111",
      })
    );
    const json = await res.json();

    expect(res.status).toBe(489);
    expect(res.headers.get("Upstash-NonRetryable-Error")).toBe("true");
    expect(json.error).toBe("rag_index_limit");
    expect(json.reason).toContain("rag_limit:too_many_chunks");
    expect(recordTelemetryEventMock).toHaveBeenCalledWith(
      "jobs.rag_index.failed",
      expect.objectContaining({
        attributes: expect.objectContaining({
          chunksCreated: 0,
          documentCount: 1,
          failedCount: 1,
          namespace: "user_content",
          retryOutcome: "non_retryable",
        }),
        level: "error",
      })
    );
  });

  it("returns 489 for invalid payload and marks as non-retryable", async () => {
    const { POST } = await loadRoute();

    const res = await POST(makeRequest({}));
    const json = await res.json();

    expect(res.status).toBe(489);
    expect(res.headers.get("Upstash-NonRetryable-Error")).toBe("true");
    expect(json.error).toBe("invalid_request");
    expect(json.reason).toBe("Request validation failed");
  });

  afterAll(() => {
    upstashAfterAllHook();
  });
});
