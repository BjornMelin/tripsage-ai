# Prompt: Observability (Telemetry, Spans, Counters) + Redaction + Rate Limits

## Executive summary

- Goal: Add structured telemetry across BYOK RPCs, provider calls, and tools; ensure redaction of `api_key`; enforce rate limits on key endpoints.

## Custom persona

- You are “AI SDK Migrator (Observability)”. You make debugging seamless and secure.

## Docs & references

- AI SDK telemetry docs (Core) and Next.js instrumentation
- Vercel AI Gateway app attribution (optional): <https://vercel.com/docs/ai-gateway/app-attribution>
- exa.crawling_exa telemetry docs; firecrawl_scrape Gateway attribution
- exa.get_code_context_exa for instrumentation examples; exa.web_search_exa for redaction patterns
- zen.planner; zen.analyze; zen.secaudit (ensure logs do not leak secrets)
- zen.consensus for rate-limit and telemetry schema decisions (≥ 9.0/10)
- zen.challenge; zen.codereview

## Plan (overview)

1) Telemetry module `frontend/lib/observability/index.ts` exporting span helpers
2) Wrap BYOK RPCs and chat provider calls with spans; counters for errors/usage
3) Implement log redaction middleware/util; scrub `api_key` fields
4) Add rate limits: strict for `/api/keys*` routes; moderate for `/api/chat*`
5) Vitest tests: unit for redaction utils; integration smoke for rate limit headers

## Checklist (mark off; add notes under each)

- [ ] Implement `frontend/lib/observability/index.ts` with span/counter helpers
  - Notes:
- [ ] Instrument BYOK RPCs and provider calls
  - Notes:
- [ ] Implement redaction util for `api_key` and other sensitive fields
  - Notes:
- [x] Add rate limits to `/api/keys*` and `/api/chat*`
  - Notes:
- [ ] Vitest tests: redaction + rate-limit smoke
  - Notes:
- [ ] Write ADR(s) and Spec(s) for telemetry schema and policies
  - Notes:

### Augmented checklist (AI SDK v6 specifics)

- [x] Attach usage/tokens via `messageMetadata` on finish; include `model` and provider id
  - Notes: surface in final UI messages; omit raw prompts from logs
- [ ] Classify errors (provider vs user input vs rate-limit); add counters
- [x] Emit `Retry-After` header on 429; never log full request bodies or secrets
- [ ] Degrade gracefully when OTEL exporters unavailable; never block routes

## Working instructions (mandatory)

- Check off tasks only after Vitest/biome/tsc are clean.
- Add “Notes” per task; address or log follow-ups.
- Write ADR(s) in `docs/adrs/` for observability/telemetry decisions (span names, counters, PII policy), and Spec(s) in `docs/specs/` describing schema and implementation details.

## Process flow (required)

1) Research: exa.web_search_exa → exa.crawling_exa → firecrawl_scrape → exa.get_code_context_exa for telemetry patterns and redaction best practices.
2) Plan: zen.planner; define atomic tasks.
3) Deep design: zen.thinkdeep + zen.analyze to define span names, counters, and PII policy.
4) Decide: zen.consensus (≥ 9.0/10) on telemetry schema; revise if needed.
5) Draft docs: ADR(s)/Spec(s) for observability policy and implementation.
6) Security review: zen.secaudit (ensure no secrets in logs and spans).
7) Implement: code + tests; keep Biome/tsc clean.
8) Challenge: zen.challenge assumptions.
9) Review: zen.codereview; fix; rerun checks.
10) Finalize docs: update ADR/Spec with deltas.

## Legacy mapping (delete later)

- Python logging/observability for these features (triplicate code)

## Testing requirements (Vitest)

- Ensure no sensitive fields appear in logs

## Final Notes & Next Steps (compile from task notes)

- Summary of changes and decisions:
- Outstanding items / tracked tech debt:
- Follow-up prompts or tasks:

## Additional context & assumptions

- Span naming conventions:
  - `svc.db.vault.rpc` for Vault RPC calls
  - `svc.provider.complete` for provider completions
  - `svc.tools.execute` for tool executions
- Counters:
  - `svc.op.errors_total` (labeled by operation)
  - `svc.op.usage_tokens_total` (prompt/completion)
- Rate-limit libraries: e.g., `@upstash/ratelimit` or similar; attach headers for RL status.

## File & module targets

- `frontend/lib/observability/index.ts` (spans/counters)
- `frontend/lib/logging/redact.ts` (scrub api_key and similar)
- Rate-limit middleware under `frontend/middleware.ts` or per-route wrappers

## Security checks

- Verify redaction is applied in error paths and logs; run zen.secaudit to confirm no leakage.
