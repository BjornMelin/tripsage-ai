/**
 * @fileoverview Pure handler for attachment ingestion jobs (download + text extraction).
 */

import "server-only";

import { ATTACHMENT_MAX_FILE_SIZE } from "@schemas/attachments";
import {
  MAX_RAG_EMBED_CHUNKS_PER_BATCH,
  MAX_RAG_INDEX_JOB_BODY_BYTES,
  MAX_RAG_INDEX_TOTAL_CONTENT_CHARS,
  RAG_CHARS_PER_TOKEN,
  RAG_INDEX_QSTASH_TIMEOUT_SECONDS,
} from "@schemas/rag";
import type { AttachmentsIngestJob, RagIndexJob } from "@schemas/webhooks";
import type { EnqueueJobOptions } from "@/lib/qstash/client";
import { QSTASH_JOB_LABELS } from "@/lib/qstash/config";
import type { TypedAdminSupabase } from "@/lib/supabase/admin";
import { getMaybeSingle } from "@/lib/supabase/typed-helpers";
import { createServerLogger } from "@/lib/telemetry/logger";
import { recordTelemetryEvent } from "@/lib/telemetry/span";

const logger = createServerLogger("jobs.attachments-ingest");
const STORAGE_BUCKET = "attachments";

// Keep job payloads bounded and avoid runaway embedding costs.
const MAX_EXTRACTED_TEXT_CHARS = MAX_RAG_INDEX_TOTAL_CONTENT_CHARS;
const MAX_PDF_PAGES = 50;

export interface AttachmentsIngestDeps {
  supabase: TypedAdminSupabase;
  tryEnqueueJob: (
    jobType: string,
    payload: unknown,
    path: string,
    options: EnqueueJobOptions
  ) => Promise<
    | { success: true; messageId: string; deduplicated?: boolean }
    | { success: false; error: Error | null }
  >;
}

export class NonRetryableJobError extends Error {
  public readonly errorCode: string;

  constructor(errorCode: string, message: string) {
    super(message);
    this.errorCode = errorCode;
    this.name = "NonRetryableJobError";
  }
}

function roundDurationMs(durationMs: number): number {
  return Math.round(durationMs * 100) / 100;
}

function estimateRagChunkCount(params: {
  chunkOverlap: number;
  chunkSize: number;
  contentChars: number;
}): number {
  const estimatedChunkChars = Math.max(
    1,
    (params.chunkSize - params.chunkOverlap) * RAG_CHARS_PER_TOKEN
  );
  return Math.ceil(params.contentChars / estimatedChunkChars);
}

function getJsonByteLength(value: unknown): number {
  return Buffer.byteLength(JSON.stringify(value), "utf8");
}

function recordAttachmentIngestEvent(
  eventName: string,
  startedAt: number,
  attributes: Record<string, boolean | number | string>
): void {
  recordTelemetryEvent(eventName, {
    attributes: {
      ...attributes,
      durationMs: roundDurationMs(performance.now() - startedAt),
    },
    level: eventName.endsWith(".failed") ? "error" : "info",
  });
}

function normalizeExtractedText(text: string): string {
  const normalized = text.normalize("NFC");
  let cleaned = "";
  for (let i = 0; i < normalized.length; i += 1) {
    const code = normalized.charCodeAt(i);
    const isControl =
      code <= 8 ||
      code === 11 ||
      code === 12 ||
      (code >= 14 && code <= 31) ||
      code === 127;
    if (!isControl) {
      cleaned += normalized[i] ?? "";
    }
  }
  return cleaned.trim();
}

async function downloadStorageObjectToBuffer(params: {
  bucket: string;
  maxBytes?: number;
  path: string;
  supabase: TypedAdminSupabase;
}): Promise<Buffer> {
  const { bucket, maxBytes, path, supabase } = params;
  const { data, error } = await supabase.storage.from(bucket).download(path);
  if (error || !data) {
    throw new Error(`storage_download_failed:${error?.message ?? "no_data"}`);
  }

  if (maxBytes != null && data.size > maxBytes) {
    throw new NonRetryableJobError(
      "file_too_large",
      "Attachment exceeds supported size"
    );
  }

  const bytes = await data.arrayBuffer();
  if (maxBytes != null && bytes.byteLength > maxBytes) {
    throw new NonRetryableJobError(
      "file_too_large",
      "Attachment exceeds supported size"
    );
  }
  return Buffer.from(bytes);
}

async function extractTextFromBuffer(params: {
  buffer: Buffer;
  mimeType: string;
  originalFilename: string;
}): Promise<{ ok: true; text: string } | { ok: false; reason: "unsupported_mime" }> {
  const { buffer, mimeType, originalFilename } = params;

  switch (mimeType) {
    case "text/plain":
    case "text/csv": {
      return { ok: true, text: buffer.toString("utf8") };
    }

    case "application/pdf": {
      const { PDFParse } = await import("pdf-parse");
      const parser = new PDFParse({ data: buffer });
      const parsed = await parser.getText({ first: MAX_PDF_PAGES });
      return { ok: true, text: parsed.text };
    }

    case "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
      const mammoth = await import("mammoth");
      const parsed = await mammoth.extractRawText({ buffer });
      return { ok: true, text: parsed.value };
    }

    case "application/msword": {
      logger.info("unsupported_doc_format", {
        hasOriginalFilename: Boolean(originalFilename),
      });
      return { ok: false, reason: "unsupported_mime" };
    }

    default: {
      logger.info("unsupported_mime_type", {
        hasOriginalFilename: Boolean(originalFilename),
        mimeType,
      });
      return { ok: false, reason: "unsupported_mime" };
    }
  }
}

export async function handleAttachmentsIngest(
  deps: AttachmentsIngestDeps,
  job: AttachmentsIngestJob
): Promise<
  | {
      ok: true;
      queued: boolean;
      ragMessageId?: string;
      skipped?: boolean;
      skipReason?: string;
    }
  | {
      ok: true;
      queued: boolean;
      extractedChars?: number;
      extractedCharsOriginal?: number;
      ragMessageId?: string;
      truncated?: boolean;
    }
> {
  const { supabase } = deps;
  const startedAt = performance.now();
  let fileSizeBytes = 0;
  let mimeType = "unknown";
  let extractedCharsOriginal = 0;
  let extractedCharsUsed = 0;
  let estimatedChunks = 0;
  let ragPayloadBytes = 0;

  try {
    const { data: attachment, error } = await getMaybeSingle(
      supabase,
      "file_attachments",
      (qb) => qb.eq("id", job.attachmentId),
      {
        select:
          "id,bucket_name,file_path,file_size,mime_type,original_filename,upload_status,virus_scan_status,user_id,trip_id,chat_id",
        validate: false,
      }
    );

    if (error) {
      const message =
        error instanceof Error
          ? error.message
          : error && typeof error === "object" && "message" in error
            ? String((error as { message?: unknown }).message ?? error)
            : String(error);
      throw new Error(`db_error:${message}`);
    }

    if (!attachment) {
      throw new NonRetryableJobError("not_found", "Attachment does not exist");
    }

    fileSizeBytes = attachment.file_size;
    mimeType = attachment.mime_type;

    if (attachment.upload_status !== "completed") {
      throw new Error("upload_not_completed");
    }

    if (attachment.virus_scan_status === "infected") {
      throw new NonRetryableJobError(
        "virus_infected",
        "Attachment is flagged as infected"
      );
    }

    if (attachment.bucket_name !== STORAGE_BUCKET) {
      throw new NonRetryableJobError(
        "invalid_bucket",
        `Unexpected attachment bucket: ${attachment.bucket_name}`
      );
    }

    if (attachment.file_size > ATTACHMENT_MAX_FILE_SIZE) {
      throw new NonRetryableJobError(
        "file_too_large",
        "Attachment exceeds supported size"
      );
    }

    const buffer = await downloadStorageObjectToBuffer({
      bucket: attachment.bucket_name,
      maxBytes: ATTACHMENT_MAX_FILE_SIZE,
      path: attachment.file_path,
      supabase,
    });

    const extracted = await extractTextFromBuffer({
      buffer,
      mimeType: attachment.mime_type,
      originalFilename: attachment.original_filename,
    });

    if (!extracted.ok) {
      recordAttachmentIngestEvent("jobs.attachments_ingest.skipped", startedAt, {
        fileSizeBytes,
        mimeType,
        retryOutcome: "not_applicable",
        skipReason: extracted.reason,
      });
      return {
        ok: true,
        queued: false,
        skipped: true,
        skipReason: extracted.reason,
      };
    }

    const normalized = normalizeExtractedText(extracted.text);
    if (normalized.length === 0) {
      recordAttachmentIngestEvent("jobs.attachments_ingest.skipped", startedAt, {
        fileSizeBytes,
        mimeType,
        retryOutcome: "not_applicable",
        skipReason: "empty_text",
      });
      return {
        ok: true,
        queued: false,
        skipped: true,
        skipReason: "empty_text",
      };
    }

    extractedCharsOriginal = normalized.length;
    let text = normalized;
    let truncated = false;
    if (text.length > MAX_EXTRACTED_TEXT_CHARS) {
      truncated = true;
      text = text.slice(0, MAX_EXTRACTED_TEXT_CHARS);
      logger.warn("extracted_text_truncated", {
        extractedCharsOriginal,
        extractedCharsUsed: text.length,
        hasAttachmentId: true,
      });
    }
    extractedCharsUsed = text.length;

    const chunkSize = 512;
    const chunkOverlap = 100;
    estimatedChunks = estimateRagChunkCount({
      chunkOverlap,
      chunkSize,
      contentChars: text.length,
    });
    if (estimatedChunks > MAX_RAG_EMBED_CHUNKS_PER_BATCH) {
      throw new NonRetryableJobError(
        "rag_chunk_budget_exceeded",
        "Attachment text would exceed the RAG chunk budget"
      );
    }

    const ragJob: RagIndexJob = {
      chatId: attachment.chat_id ?? null,
      chunkOverlap,
      chunkSize,
      documents: [
        {
          content: text,
          id: job.attachmentId,
          metadata: {
            attachmentId: job.attachmentId,
            extractedCharsOriginal,
            extractedCharsUsed: text.length,
            filePath: attachment.file_path,
            mimeType: attachment.mime_type,
            originalFilename: attachment.original_filename,
            truncated,
          },
          sourceId: job.attachmentId,
        },
      ],
      namespace: "user_content",
      tripId: attachment.trip_id ?? null,
      userId: attachment.user_id,
    };

    ragPayloadBytes = getJsonByteLength(ragJob);
    if (ragPayloadBytes > MAX_RAG_INDEX_JOB_BODY_BYTES) {
      throw new NonRetryableJobError(
        "rag_payload_too_large",
        "RAG index job payload exceeds the QStash budget"
      );
    }

    const enqueue = await deps.tryEnqueueJob(
      "rag-index",
      ragJob,
      "/api/jobs/rag-index",
      {
        deduplicationId: `rag-index:attachment:${job.attachmentId}`,
        label: QSTASH_JOB_LABELS.RAG_INDEX,
        timeout: RAG_INDEX_QSTASH_TIMEOUT_SECONDS,
      }
    );

    if (!enqueue.success) {
      throw enqueue.error ?? new Error("qstash_unavailable");
    }

    recordAttachmentIngestEvent("jobs.attachments_ingest.completed", startedAt, {
      estimatedChunks,
      extractedCharsOriginal,
      extractedCharsUsed,
      fileSizeBytes,
      mimeType,
      qstashDeduplicated: enqueue.deduplicated ?? false,
      ragPayloadBytes,
      retryOutcome: "not_applicable",
      truncated,
    });

    return {
      extractedChars: text.length,
      extractedCharsOriginal: truncated ? extractedCharsOriginal : undefined,
      ok: true,
      queued: true,
      ragMessageId: enqueue.messageId,
      truncated: truncated ? true : undefined,
    };
  } catch (error) {
    const nonRetryable = error instanceof NonRetryableJobError;
    recordAttachmentIngestEvent("jobs.attachments_ingest.failed", startedAt, {
      errorCode: nonRetryable ? error.errorCode : "retryable_error",
      estimatedChunks,
      extractedCharsOriginal,
      extractedCharsUsed,
      fileSizeBytes,
      mimeType,
      ragPayloadBytes,
      retryOutcome: nonRetryable ? "non_retryable" : "retryable",
    });
    throw error;
  }
}
