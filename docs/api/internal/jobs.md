# Background Jobs

Background job endpoints delivered by Upstash QStash.

> **Access**: These endpoints must only be called by Upstash QStash. They verify `Upstash-Signature` against the **raw request body**.

## Common behavior

- **Signature verification**: Rejects requests without a valid `Upstash-Signature` before JSON parsing.
- **Idempotency (delivery-level)**: Uses `Upstash-Message-Id` (stable across retries) to ensure each QStash message is processed once.
  - If already processed: returns `200` with `{ ok: true, duplicate: true }`.
  - If another worker is processing the same message: returns `409` to trigger a retry.
- **Retries**:
  - Any **non-2xx** response triggers a retry (until QStash retry limit is reached).
  - Retry delay behavior is configured on publish via `Upstash-Retry-Delay` (see `src/lib/qstash/client.ts`).
  - **Non-retryable** failures return `489` with `Upstash-NonRetryable-Error: true` (QStash forwards to DLQ if configured).
- **Publishing contract**: every publish through `enqueueJob()`/`tryEnqueueJob()`
  must include a deterministic `deduplicationId` and a canonical `label` from
  `QSTASH_JOB_LABELS`; the helper always sends the configured retry count and
  retry-delay expression.
- **DLQ operations**: Filter by `label`, message URL, or `Upstash-Message-Id` in
  the Upstash Console or the QStash DLQ API, then **republish** after fixing the
  root cause or **delete** when the payload is obsolete/non-replayable.
- **Production degradation**: job enqueue failures on production webhook paths
  must fail closed. Local/test-only in-process fallbacks must be explicitly gated.

## Attachment and RAG budgets

The attachment ingest to RAG index path is intentionally bounded before any
workflow-orchestration rewrite:

| Budget | Value | Owner |
| --- | ---: | --- |
| Vercel function max duration | 60s | `vercel.json` |
| QStash RAG delivery timeout | 55s | `RAG_INDEX_QSTASH_TIMEOUT_SECONDS` |
| Embedding abort timeout | 50s | `RAG_INDEX_EMBED_TIMEOUT_BUDGET_MS` |
| QStash RAG request body cap | 512 KiB | `MAX_RAG_INDEX_JOB_BODY_BYTES` |
| QStash documented default message-size limit | 1 MiB | Upstash QStash docs |
| Attachment download cap | 10 MiB | `ATTACHMENT_MAX_FILE_SIZE` |
| Extracted text cap | 250,000 chars | `MAX_RAG_INDEX_TOTAL_CONTENT_CHARS` |
| Documents per RAG job | 100 | `MAX_RAG_INDEX_DOCUMENTS` |
| Chunks per embedding batch | 1,200 | `MAX_RAG_EMBED_CHUNKS_PER_BATCH` |

Telemetry must stay redacted and low-cardinality. The job path records counts
and durations only:

- `jobs.attachments_ingest.completed`: duration, file size, MIME type,
  extracted char counts, estimated chunk count, serialized RAG payload bytes,
  truncation, retry outcome, and QStash deduplication result.
- `jobs.attachments_ingest.skipped`: duration, file size, MIME type, skip
  reason, and retry outcome.
- `jobs.attachments_ingest.failed`: duration, file size, MIME type, extracted
  char counts, estimated chunk count, serialized RAG payload bytes, error code,
  and retry outcome.
- `jobs.rag_index.completed|failed`: document count, chunk count, indexed and
  failed counts, namespace, and retry outcome.
- `rag.indexer.index_complete`: duration, document/chunk counts, embedding
  calls, embedding token usage, embedding warnings, DB upsert count, DB rows
  upserted, indexed count, failed count, and namespace.
- `rag.indexer.embedding_failed`: chunk count, document count, namespace, and
  provider error class name; never raw document content or provider payloads.

The attachment-to-RAG QStash message body is a raw user-content processor
boundary: it carries extracted document content and attachment metadata so the
worker can index asynchronously, and retryable failures can leave that body in
QStash retry/DLQ storage. Treat QStash credentials, DLQ access, and payload
inspection as sensitive production data access. The publisher must request
provider-side request-body log redaction for this message. Telemetry must only
record redacted aggregate counters and hashes, never the payload content or
sensitive metadata such as filenames and storage paths.

Open a separate Upstash Workflow pilot issue only if production telemetry shows
one of these conditions for the attachment/RAG path:

- sustained P95 job duration above 45s or recurring 60s function timeouts;
- repeated QStash delivery timeout or retry/DLQ events for the same budget
  class after input caps are enforced;
- embedding calls or DB upserts require multi-step checkpointing that would
  delete more custom state code than the workflow SDK adds;
- operator cost traces show runaway embedding volume that cannot be solved with
  tighter payload/chunk/batch limits.

## Job ownership and publish labels

| Job | Owner | Worker | Publish label | Dedup key shape |
| --- | --- | --- | --- | --- |
| Attachment ingest | File webhook | `/api/jobs/attachments-ingest` | `tripsage:attachments-ingest` | `attachments-ingest:<attachmentId>` |
| RAG index | Attachment ingest | `/api/jobs/rag-index` | `tripsage:rag-index` | `rag-index:attachment:<attachmentId>` |
| Memory sync | Memory adapter | `/api/jobs/memory-sync` | `tripsage:memory-sync` | `memory-sync:<sync-idempotency-key>` |
| Collaborator notifications | Trip webhook | `/api/jobs/notify-collaborators` | `tripsage:notify-collaborators` | `notify:<eventKey>` |

## Local QStash development

Use the shared mocks for unit tests. For local integration, set
`UPSTASH_USE_EMULATOR=1`, point `UPSTASH_REDIS_REST_URL` at the Redis REST
emulator, and set `UPSTASH_QSTASH_DEV_URL` to the QStash dev server endpoint.
`UPSTASH_EMULATOR_URL` remains a legacy Redis alias only.

Live smoke tests use production-compatible env names for credentials:
`UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`, and `QSTASH_TOKEN`.
Set `UPSTASH_QSTASH_SMOKE_TARGET_URL` to a disposable request-bin style URL
before running `UPSTASH_SMOKE=1 pnpm test:upstash:smoke`.

---

## `POST /api/jobs/notify-collaborators`

Notify trip collaborators from a Supabase webhook event (enqueued by `/api/hooks/trips`).

### Request body

```json
{
  "eventKey": "string",
  "payload": {
    "table": "string",
    "type": "INSERT|UPDATE|DELETE",
    "record": { "..." : "..." },
    "oldRecord": { "..." : "..." } ,
    "schema": "public",
    "occurredAt": "2026-01-01T00:00:00.000Z"
  }
}
```

### Responses

- `200 OK`: `{ ok: true }` (or `{ ok: true, duplicate: true }`)
- `401 Unauthorized`: invalid/missing QStash signature
- `409 Conflict`: message is already being processed (retryable)
- `489`: invalid request body (non-retryable)
- `500`: internal error (retryable)

---

## `POST /api/jobs/memory-sync`

Persist conversation turns and update memory sync markers for a chat session.

### Request body

```json
{
  "idempotencyKey": "string",
  "payload": {
    "sessionId": "uuid",
    "userId": "uuid",
    "syncType": "full|incremental|conversation",
    "conversationMessages": [
      {
        "role": "user|assistant|system",
        "content": "string",
        "timestamp": "2026-01-01T00:00:00.000Z",
        "metadata": {}
      }
    ]
  }
}
```

### Responses

- `200 OK`: `{ ok: true, ... }` (or `{ ok: true, duplicate: true }`)
- `401 Unauthorized`: invalid/missing QStash signature
- `409 Conflict`: message is already being processed (retryable)
- `489`: invalid request body (non-retryable)
- `500`: internal error (retryable)

---

## `POST /api/jobs/attachments-ingest`

Ingest a single uploaded attachment: download from Supabase Storage, extract text, then enqueue a RAG indexing job.

The worker caps extracted text at 250,000 characters, validates the serialized
RAG job payload against the 512 KiB QStash body budget, estimates chunk fan-out
before enqueueing, and sets a 55s QStash delivery timeout for `/api/jobs/rag-index`.

### Request body

```json
{ "attachmentId": "uuid" }
```

### Responses

- `200 OK`:
  - `{ ok: true, queued: true, ragMessageId: "..." }`
  - `{ ok: true, queued: false, skipped: true, skipReason: "unsupported_mime|empty_text" }`
  - `{ ok: true, duplicate: true }`
- `401 Unauthorized`: invalid/missing QStash signature
- `409 Conflict`: message is already being processed (retryable)
- `489`: invalid request body or non-retryable attachment error (DLQ)
- `500`: internal error (retryable)

---

## `POST /api/jobs/rag-index`

Index documents into the RAG store (chunking + embeddings + storage).

The worker rejects request bodies over 512 KiB before JSON parsing, validates
chunk overlap is smaller than chunk size, maps RAG budget-limit failures to
HTTP `489`, and records embedding/DB cost counters without content.

### Request body

```json
{
  "userId": "uuid",
  "tripId": 123,
  "chatId": "uuid",
  "namespace": "default|accommodations|destinations|activities|travel_tips|user_content",
  "chunkSize": 512,
  "chunkOverlap": 100,
  "documents": [
    { "id": "uuid", "sourceId": "string", "content": "string", "metadata": {} }
  ]
}
```

### Responses

- `200 OK`: standard RAG index response (`success: true`)
- `401 Unauthorized`: invalid/missing QStash signature
- `409 Conflict`: message is already being processed (retryable)
- `489`: invalid request body (non-retryable)
- `500`: internal error (retryable)
