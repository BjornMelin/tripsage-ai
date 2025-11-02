# Spec: SSE Chat Streaming (End-to-End)

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-10-24

## Objective

Deliver server-sent events (SSE) chat streaming via Next.js AI SDK v6 Route Handler and a streaming-capable frontend hook. JSON non-stream is provided by `/api/chat`.

## Scope

- Next.js Route: `POST /api/chat/stream` responds with `toUIMessageStreamResponse()` and emits token deltas.
- Frontend: `use-chat-ai` posts to `/api/chat/stream`, updates a placeholder assistant message as deltas arrive, and supports cancellation.
- No feature flags; streaming is the final implementation.

## API Contract

- Method: `POST /api/chat/stream`
- Request JSON (subset):
  - `messages`: array of `{ role: 'user'|'assistant'|'system', content: string }`
  - `session_id` (optional UUID)
  - `temperature`, `max_tokens` (optional)
- Response: `text/event-stream` framed with lines `data: <json>\n\n`
  - `{"type":"started","user":"<id>"}` (once)
  - `{"type":"delta","content":"<string>"}` (0..N)
  - `{"type":"final","content":"<string>"}` (once)
  - `[DONE]` sentinel
- Error: `{"type":"error","message":"..."}` as an SSE event, then stream ends.

## Frontend Hook Behavior (`use-chat-ai`)

- Create a placeholder assistant message before reading the stream; append `delta` tokens as they arrive.
- Use `AbortController` to support user cancellation and a 60s timeout.
- Ensure session creation updates `sessionIdRef.current` before further store mutations.
- Perform immutable Map updates for tool-call state.

## Non-Goals

- Tool-call event streaming over SSE (future).
- AI SDK UI wrapper conversion (future; backend format is compatible with adapters).

## Implementation Notes

- Backend: LangChain `ChatOpenAI(..., streaming=True)` and `llm.astream(...)` power the generator; each token yields a delta event.
- Frontend: Parse SSE by splitting on `\n\n` and handling `data:` lines only. Ignore malformed lines.

## Testing

- Frontend unit test: mock `fetch` to return a ReadableStream that emits one `delta` and `[DONE]`; verify placeholder update call fires.
- Backend integration test (follow-up): ensure correct event framing and disconnect handling.

## Changelog

- 1.0.0 (2025-10-24)
  - Initial end-to-end SSE streaming spec and implementation.
