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
- **DLQ operations**: Use the Upstash Console to **republish** or **delete** DLQ messages.

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
