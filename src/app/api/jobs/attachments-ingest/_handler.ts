/**
 * @fileoverview Pure handler for attachment ingestion jobs (download + text extraction).
 */

import "server-only";

import { ATTACHMENT_MAX_FILE_SIZE } from "@schemas/attachments";
import type { AttachmentsIngestJob, RagIndexJob } from "@schemas/webhooks";
import type { EnqueueJobOptions } from "@/lib/qstash/client";
import { QSTASH_JOB_LABELS } from "@/lib/qstash/config";
import type { TypedAdminSupabase } from "@/lib/supabase/admin";
import { getMaybeSingle } from "@/lib/supabase/typed-helpers";
import { createServerLogger } from "@/lib/telemetry/logger";

const logger = createServerLogger("jobs.attachments-ingest");
const STORAGE_BUCKET = "attachments";

// Keep job payloads bounded and avoid runaway embedding costs.
const MAX_EXTRACTED_TEXT_CHARS = 250_000;
const MAX_PDF_PAGES = 50;

export interface AttachmentsIngestDeps {
  supabase: TypedAdminSupabase;
  tryEnqueueJob: (
    jobType: string,
    payload: unknown,
    path: string,
    options?: EnqueueJobOptions
  ) => Promise<
    { success: true; messageId: string } | { success: false; error: Error | null }
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
      logger.info("unsupported_doc_format", { originalFilename });
      return { ok: false, reason: "unsupported_mime" };
    }

    default: {
      logger.info("unsupported_mime_type", { mimeType, originalFilename });
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
    return {
      ok: true,
      queued: false,
      skipped: true,
      skipReason: extracted.reason,
    };
  }

  const normalized = normalizeExtractedText(extracted.text);
  if (normalized.length === 0) {
    return {
      ok: true,
      queued: false,
      skipped: true,
      skipReason: "empty_text",
    };
  }

  const extractedCharsOriginal = normalized.length;
  let text = normalized;
  let truncated = false;
  if (text.length > MAX_EXTRACTED_TEXT_CHARS) {
    truncated = true;
    text = text.slice(0, MAX_EXTRACTED_TEXT_CHARS);
    logger.warn("extracted_text_truncated", {
      attachmentId: job.attachmentId,
      extractedCharsOriginal,
      extractedCharsUsed: text.length,
    });
  }

  const ragJob: RagIndexJob = {
    chatId: attachment.chat_id ?? null,
    chunkOverlap: 100,
    chunkSize: 512,
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

  const enqueue = await deps.tryEnqueueJob("rag-index", ragJob, "/api/jobs/rag-index", {
    deduplicationId: `rag-index:attachment:${job.attachmentId}`,
    label: QSTASH_JOB_LABELS.RAG_INDEX,
  });

  if (!enqueue.success) {
    throw enqueue.error ?? new Error("qstash_unavailable");
  }

  return {
    extractedChars: text.length,
    extractedCharsOriginal: truncated ? extractedCharsOriginal : undefined,
    ok: true,
    queued: true,
    ragMessageId: enqueue.messageId,
    truncated: truncated ? true : undefined,
  };
}
