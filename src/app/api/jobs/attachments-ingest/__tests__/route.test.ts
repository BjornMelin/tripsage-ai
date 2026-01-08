/** @vitest-environment node */

import { ATTACHMENT_MAX_FILE_SIZE } from "@schemas/attachments";
import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import { setupUpstashTestEnvironment } from "@/test/upstash/setup";

const {
  afterAllHook: upstashAfterAllHook,
  beforeEachHook: upstashBeforeEachHook,
  mocks: upstashMocks,
} = setupUpstashTestEnvironment();

type TryEnqueueJob = (
  jobType: string,
  payload: unknown,
  path: string,
  options?: { deduplicationId?: string }
) => Promise<
  { success: true; messageId: string } | { success: false; error: Error | null }
>;

const envStore = vi.hoisted<Record<string, string | undefined>>(() => ({
  QSTASH_CURRENT_SIGNING_KEY: "current",
  QSTASH_NEXT_SIGNING_KEY: "next",
  UPSTASH_REDIS_REST_TOKEN: "token",
  UPSTASH_REDIS_REST_URL: "https://example.upstash.local",
}));

const tryEnqueueJobMock = vi.hoisted(() => vi.fn<TryEnqueueJob>());
const createAdminSupabaseMock = vi.hoisted(() => vi.fn());

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

vi.mock("@/lib/qstash/client", () => ({
  tryEnqueueJob: (
    jobType: string,
    payload: unknown,
    path: string,
    options?: { deduplicationId?: string }
  ) => tryEnqueueJobMock(jobType, payload, path, options),
}));

vi.mock("@/lib/supabase/admin", () => ({
  createAdminSupabase: () => createAdminSupabaseMock(),
}));

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: vi.fn(),
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
  return new Request("http://localhost/api/jobs/attachments-ingest", {
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

function createSupabaseStub(params: {
  attachment: Record<string, unknown> | null;
  downloadBlob?: Blob | null;
}) {
  const maybeSingle = vi.fn(async () => ({ data: params.attachment, error: null }));
  const eq = vi.fn(() => ({ maybeSingle }));
  const select = vi.fn(() => ({ eq }));
  const from = vi.fn(() => ({ select }));

  const download = vi.fn(async () => ({
    data: params.downloadBlob ?? null,
    error: null,
  }));
  const storage = { from: vi.fn(() => ({ download })) };

  return { from, storage };
}

describe("POST /api/jobs/attachments-ingest", () => {
  beforeEach(() => {
    upstashBeforeEachHook();
    vi.clearAllMocks();
    tryEnqueueJobMock.mockReset();
    tryEnqueueJobMock.mockResolvedValue({ messageId: "rag-1", success: true });
    createAdminSupabaseMock.mockReset();
    upstashMocks.qstash.__forceVerify(true);

    createAdminSupabaseMock.mockReturnValue(
      createSupabaseStub({
        attachment: {
          bucket_name: "attachments",
          chat_id: "123e4567-e89b-12d3-a456-426614174000",
          file_path: "u/c/a/file.txt",
          file_size: 1024,
          id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
          mime_type: "text/plain",
          original_filename: "file.txt",
          trip_id: null,
          upload_status: "completed",
          user_id: "11111111-1111-4111-8111-111111111111",
          virus_scan_status: "clean",
        },
        downloadBlob: new Blob(["Hello world"]),
      })
    );
  });

  const loadRoute = async () => await import("../route");

  it("ingests text and enqueues a rag-index job", async () => {
    const { POST } = await loadRoute();

    const res = await POST(
      makeRequest({ attachmentId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" })
    );
    const json = await res.json();

    expect(res.status).toBe(200);
    expect(json.ok).toBe(true);
    expect(json.queued).toBe(true);
    expect(json.ragMessageId).toBe("rag-1");
    expect(json.extractedChars).toBeGreaterThan(0);
    expect(tryEnqueueJobMock).toHaveBeenCalledWith(
      "rag-index",
      expect.objectContaining({
        documents: [
          expect.objectContaining({
            id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            sourceId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
          }),
        ],
        userId: "11111111-1111-4111-8111-111111111111",
      }),
      "/api/jobs/rag-index",
      { deduplicationId: "rag-index:attachment:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" }
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
    expect(tryEnqueueJobMock).not.toHaveBeenCalled();
  });

  it("returns 489 (DLQ) when attachment does not exist", async () => {
    createAdminSupabaseMock.mockReturnValue(
      createSupabaseStub({ attachment: null, downloadBlob: null })
    );

    const { POST } = await loadRoute();

    const res = await POST(
      makeRequest({ attachmentId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" })
    );
    const json = await res.json();

    expect(res.status).toBe(489);
    expect(res.headers.get("Upstash-NonRetryable-Error")).toBe("true");
    expect(json.error).toBe("not_found");
    expect(json.reason).toBe("Attachment does not exist");
    expect(tryEnqueueJobMock).not.toHaveBeenCalled();
  });

  it("returns 489 (DLQ) when attachment file size exceeds limit", async () => {
    createAdminSupabaseMock.mockReturnValue(
      createSupabaseStub({
        attachment: {
          bucket_name: "attachments",
          chat_id: "123e4567-e89b-12d3-a456-426614174000",
          file_path: "u/c/a/file.txt",
          file_size: 10 * 1024 * 1024 + 1,
          id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
          mime_type: "text/plain",
          original_filename: "file.txt",
          trip_id: null,
          upload_status: "completed",
          user_id: "11111111-1111-4111-8111-111111111111",
          virus_scan_status: "clean",
        },
        downloadBlob: new Blob(["Hello world"]),
      })
    );

    const { POST } = await loadRoute();

    const res = await POST(
      makeRequest({ attachmentId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" })
    );
    const json = await res.json();

    expect(res.status).toBe(489);
    expect(res.headers.get("Upstash-NonRetryable-Error")).toBe("true");
    expect(json.error).toBe("file_too_large");
    expect(tryEnqueueJobMock).not.toHaveBeenCalled();
  });

  it("returns 489 (DLQ) when downloaded blob exceeds limit even if metadata is small", async () => {
    createAdminSupabaseMock.mockReturnValue(
      createSupabaseStub({
        attachment: {
          bucket_name: "attachments",
          chat_id: "123e4567-e89b-12d3-a456-426614174000",
          file_path: "u/c/a/file.txt",
          file_size: 1024,
          id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
          mime_type: "text/plain",
          original_filename: "file.txt",
          trip_id: null,
          upload_status: "completed",
          user_id: "11111111-1111-4111-8111-111111111111",
          virus_scan_status: "clean",
        },
        downloadBlob: new Blob([new Uint8Array(ATTACHMENT_MAX_FILE_SIZE + 1)]),
      })
    );

    const { POST } = await loadRoute();

    const res = await POST(
      makeRequest({ attachmentId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" })
    );
    const json = await res.json();

    expect(res.status).toBe(489);
    expect(res.headers.get("Upstash-NonRetryable-Error")).toBe("true");
    expect(json.error).toBe("file_too_large");
    expect(tryEnqueueJobMock).not.toHaveBeenCalled();
  });

  it("returns 489 (DLQ) when attachment bucket is unexpected", async () => {
    createAdminSupabaseMock.mockReturnValue(
      createSupabaseStub({
        attachment: {
          bucket_name: "other",
          chat_id: "123e4567-e89b-12d3-a456-426614174000",
          file_path: "u/c/a/file.txt",
          file_size: 1024,
          id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
          mime_type: "text/plain",
          original_filename: "file.txt",
          trip_id: null,
          upload_status: "completed",
          user_id: "11111111-1111-4111-8111-111111111111",
          virus_scan_status: "clean",
        },
        downloadBlob: new Blob(["Hello world"]),
      })
    );

    const { POST } = await loadRoute();

    const res = await POST(
      makeRequest({ attachmentId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" })
    );
    const json = await res.json();

    expect(res.status).toBe(489);
    expect(res.headers.get("Upstash-NonRetryable-Error")).toBe("true");
    expect(json.error).toBe("invalid_bucket");
    expect(tryEnqueueJobMock).not.toHaveBeenCalled();
  });

  it("caps extracted text and marks result as truncated", async () => {
    createAdminSupabaseMock.mockReturnValue(
      createSupabaseStub({
        attachment: {
          bucket_name: "attachments",
          chat_id: "123e4567-e89b-12d3-a456-426614174000",
          file_path: "u/c/a/file.txt",
          file_size: 1024,
          id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
          mime_type: "text/plain",
          original_filename: "file.txt",
          trip_id: null,
          upload_status: "completed",
          user_id: "11111111-1111-4111-8111-111111111111",
          virus_scan_status: "clean",
        },
        downloadBlob: new Blob(["x".repeat(300_000)]),
      })
    );

    const { POST } = await loadRoute();

    const res = await POST(
      makeRequest({ attachmentId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" })
    );
    const json = await res.json();

    expect(res.status).toBe(200);
    expect(json.ok).toBe(true);
    expect(json.truncated).toBe(true);
    expect(json.extractedChars).toBe(250_000);
    expect(json.extractedCharsOriginal).toBe(300_000);
    expect(tryEnqueueJobMock).toHaveBeenCalledWith(
      "rag-index",
      expect.objectContaining({
        documents: [
          expect.objectContaining({
            content: expect.stringMatching(/^x+$/),
            metadata: expect.objectContaining({
              extractedCharsOriginal: 300_000,
              extractedCharsUsed: 250_000,
              truncated: true,
            }),
          }),
        ],
      }),
      "/api/jobs/rag-index",
      { deduplicationId: "rag-index:attachment:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" }
    );
  });

  afterAll(() => {
    upstashAfterAllHook();
  });
});
