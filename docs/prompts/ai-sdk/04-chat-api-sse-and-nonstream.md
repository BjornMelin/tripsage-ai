# Prompt: Chat API (SSE + Non-Stream) with AI SDK v6

## Executive summary

- Goal: Replace Python chat endpoints with Next.js App Router endpoints using AI SDK v6. Provide `POST /api/chat` (non-stream) and `POST /api/chat/stream` (SSE with `StreamingTextResponse`). Integrate provider registry, token clamping, and optional tools. Include tests.

## Custom persona

- You are “AI SDK Migrator (Chat)”. You implement robust SSE with graceful error handling and usage metadata where supported.

## Docs & references

- Generating Text: <https://v6.ai-sdk.dev/docs/ai-sdk-core/generating-text>
- Streaming: <https://v6.ai-sdk.dev/docs/foundations/streaming>
- Stream helpers/UI message streams: <https://v6.ai-sdk.dev/docs/ai-sdk-ui/reading-ui-message-streams>
- Use exa.crawling_exa to fetch the above; firecrawl_scrape for single-page extractions
- Use exa.get_code_context_exa for route patterns and SSE examples; exa.web_search_exa for latest best practices
- Use zen.planner for tasks; zen.thinkdeep + zen.analyze for design; zen.consensus for critical decisions (≥ 9.0/10)
- Use zen.secaudit for route exposure security check; zen.challenge for contentious assumptions; zen.codereview before completion

## Plan (overview)

1) Create `app/api/chat/route.ts` using `generateText` or `streamText(...).toAIStream()` consumed fully; return JSON { content, model, usage }
2) Create `app/api/chat/stream/route.ts` using `streamText` and return `new StreamingTextResponse(stream)`; emit started/delta/final/usage events
3) Integrate provider registry + token clamping
4) Optionally accept tools input for function-calling (to be implemented in separate tools prompt)
5) Vitest tests: Node tests for event ordering, final payload, error conditions (provider mocked)

## Checklist (mark off; add notes under each)

- [ ] Draft ADR(s) and Spec(s) (pre-implementation; research + consensus)
  - Notes:
- [ ] Implement `app/api/chat/route.ts` (non-stream)
  - Notes:
- [x] Implement `app/api/chat/stream/route.ts` (SSE with `toUIMessageStreamResponse`)
  - Notes:
- [ ] Integrate provider registry + token clamping (BYOK, per-user model)
  - Notes:
- [ ] Accept tools input for function-calling (wire to AI SDK tools registry)
  - Notes:
- [ ] Vitest tests: event ordering, final payload, error paths (provider mocked)
  - Notes:
- [ ] Finalize ADR(s) and Spec(s) for chat API design
  - Notes:

### Augmented checklist (auth, limits, sessions, attachments)

- [ ] Require Supabase SSR auth on chat routes; return 401 when unauthenticated
  - Notes: create server client via `@supabase/ssr` and gate access; mark dynamic to avoid public caching
- [ ] Upstash rate limiting on `/api/chat/stream` (e.g., 40 req/min per user+IP)
  - Notes: include Retry-After header and structured error when limited
- [ ] Persist sessions/messages to Supabase tables with Next.js Route Handlers:
  - [ ] `POST /api/chat/sessions`, `GET /api/chat/sessions`, `GET /api/chat/sessions/{id}`
  - [ ] `GET /api/chat/sessions/{id}/messages`, `POST /api/chat/sessions/{id}/messages`, `DELETE /api/chat/sessions/{id}`
  - Notes: save streamed assistant messages incrementally or on finish; SSR list with tags
- [ ] Map attachments in UI parts to model inputs (images → `type: 'image'`)
  - Notes: validate size/type; reject unsupported media with UI error part
- [ ] Resume support: include resumable ids in UI stream; enable client retry to reattach

### Observability & diagnostics

- [ ] Basic request logging (user id, model, duration); redact prompt segments
- [ ] OnFinish: surface usage (tokens) via `messageMetadata`; attach to final UI message
- [ ] Telemetry hooks (optional): measure rate-limit, error classes, and latencies

### Migration tasks

- [ ] Remove any remaining Python chat references from docs and snapshots
- [ ] Update OpenAPI snapshot to reflect removal of `/api/chat/*` Python routes

## Working instructions (mandatory)

- Check off tasks only after Vitest/biome/tsc are clean.
- Add “Notes” for implementation details, issues, and debt; address or log follow-ups.
- Write ADR(s) under `docs/adrs/` (SSE event model, non-stream contract, error policy) and Spec(s) under `docs/specs/` (schemas, examples, telemetry).

## Process flow (required)

1) Research: exa.web_search_exa → exa.crawling_exa → firecrawl_scrape → exa.get_code_context_exa for streaming patterns and SSE semantics in AI SDK v6.
2) Plan: zen.planner; define atomic tasks.
3) Deep design: zen.thinkdeep + zen.analyze for contracts, error policy, and usage metadata handling.
4) Decide: zen.consensus (≥ 9.0/10); if not, iterate.
5) Draft docs: ADR(s)/Spec(s) for non-stream + SSE routes and schemas.
6) Security review: zen.secaudit (route security, SSR-only secrets, redaction).
7) Implement: build routes + tests; keep static checks clean.
8) Challenge: zen.challenge on error handling/timeouts.
9) Review: zen.codereview; fix; re-run tests.
10) Finalize docs: update ADR/Spec with deltas.

## Legacy mapping (delete later)

- `tripsage/api/routers/chat.py`
- Python chat service logic

## Testing requirements (Vitest)

- Mock providers to assert SSE chunk sequence and final aggregation; ensure usage fields are present when reported by provider

## Final Notes & Next Steps (compile from task notes)

- Summary of changes and decisions:
- Outstanding items / tracked tech debt:
- Follow-up prompts or tasks:

## Additional context & assumptions

- Request schema (suggested):
  - Body: `{ messages: { role: 'system'|'user'|'assistant', content: string }[], model?: string, temperature?: number, maxTokens?: number, tools?: string[] }`
- Non-stream response:
  - `{ content: string, model: string, usage?: { promptTokens?: number, completionTokens?: number, totalTokens?: number } }`
- SSE events:
  - `started`: `{ type: 'started', user: string }`
  - `delta`: `{ type: 'delta', content: string }`
  - `final`: `{ type: 'final', content: string, model: string, usage?: {...} }`
  - `error`: `{ type: 'error', message: string, error_id?: string }`
- Error policy: return `500` with `{ error: 'chat_failed' }` (non-stream) or `error` event (SSE); never leak secrets.
- Sanitation: strip null bytes, limit line length if necessary, escape HTML for logs.
- Timeouts and retries: add conservative server timeout; optionally retry transient provider errors with backoff.

## File & module targets

- `frontend/app/api/chat/route.ts`
- `frontend/app/api/chat/stream/route.ts`

## Testing & mocking guidelines

- Mock providers to emit chunked deltas and optional usage; assert ordering and final aggregation.
- Test error paths: provider throws mid-stream → emit `error` event and terminate gracefully.
