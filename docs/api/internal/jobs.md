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
