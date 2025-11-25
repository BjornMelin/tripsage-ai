# Spec: Chat API (SSE + Non-Stream)

**Version**: 1.1.0  
**Status**: Accepted  
**Date**: 2025-11-04

## Endpoints

- POST `frontend/src/app/api/chat/route.ts` — Non-stream JSON
- POST `frontend/src/app/api/chat/stream/route.ts` — SSE `toUIMessageStreamResponse`

**Implementation Status:** Both endpoints are implemented. The stream endpoint integrates with memory orchestrator (`handleMemoryIntent`) for conversation persistence.

## Request

```json
{
  messages: { id: string, role: 'system'|'user'|'assistant', parts?: { type: 'text', text: string }[] }[],
  model?: string,
  temperature?: number,
  maxTokens?: number,
  tools?: string[]
}
```

## Non-stream Response

```json
{
  content: string,
  model: string,
  reasons?: string[],
  usage?: { promptTokens?: number, completionTokens?: number, totalTokens?: number },
  durationMs?: number
}
```

## SSE Events (via UIMessageStream)

- started: `{ type: 'started', user: string }`
- delta: `{ type: 'delta', content: string }`
- final: `{ type: 'final', content: string, model: string, usage?: {...} }`
- error: `{ type: 'error', message: string, error_id?: string }`

## Errors

- Non-stream: 401 `{ error: 'unauthorized' }`; 400 `{ error: 'invalid_attachment' | 'No output tokens available' }`; 500 `{ error: 'internal' }`.
- SSE: emits `error` event and terminates.

## Security

- SSR Supabase auth; no secrets in client. Stream route protected by Upstash RL (40/min user+IP).

## Memory Integration

- **Memory Orchestrator**: When `sessionId` is provided, the stream handler calls `persistMemoryTurn()` before streaming to persist user messages to Supabase via the memory orchestrator (`lib/memory/orchestrator.ts`).
- **Memory Intents**: The orchestrator handles `onTurnCommitted` intents, fanning out to Supabase (canonical), Upstash (queues), and Mem0 (optional enrichment) adapters.
- **PII Redaction**: Non-canonical adapters receive sanitized intents with PII redacted for compliance.

## Notes

- Token clamping uses `countTokens` and `getModelContextLimit`.
- Attachments limited to `image/*` (validated via `validateImageAttachments`).
- Best-effort persistence on finish with usage metadata.
- Memory persistence occurs server-side only via `handleMemoryIntent` from `lib/memory/orchestrator.ts`.
