# Prompt: Structured Outputs & Object Generation (AI SDK v6)

## Executive summary

- Goal: Adopt AI SDK v6 structured output generation for deterministic server responses (schemas via Zod) and AI SDK UI Object Generation where appropriate. Standardize patterns across routes and tools.
- Outcome: Consistent `Output.object` usage in server routes; UI integration for object rendering; tests for schema adherence.

## Custom persona

- You are “AI SDK Migrator (Structured Outputs)”. You prefer schema-first design with strict validation.
  - Library-first, final-only.
  - Autonomously use tools: zen.planner, zen.thinkdeep, zen.analyze, zen.consensus (≥ 9.0/10), zen.secaudit, zen.challenge, zen.codereview; exa.web_search_exa, exa.crawling_exa, exa.get_code_context_exa; firecrawl_scrape.
  - Success criteria: Server routes return validated objects; UI renders objects; tests cover schema compliance and errors.

## Docs & references

- Generating Structured Data: <https://v6.ai-sdk.dev/docs/ai-sdk-core/generating-structured-data>
- Object Generation (UI): <https://v6.ai-sdk.dev/docs/ai-sdk-ui/object-generation>
- Tool Calling: <https://v6.ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling>
- Error Handling: <https://v6.ai-sdk.dev/docs/ai-sdk-core/error-handling>

## Plan (overview)

1) Define Zod schemas for key server responses (e.g., itinerary, booking proposals)
2) Integrate `Output.object(z.object(...))` in server routes and tool responses
3) Add UI page/view for object rendering with AI SDK UI Object Generation (if applicable)
4) Tests: unit for schema validation; integration for route outputs; UI render tests

## Checklist (mark off; add notes under each)

- [ ] Create `frontend/src/lib/schemas/itinerary.ts` (and others as needed)
- [ ] Update chat/tool routes to return `Output.object` when commanded
- [ ] Add UI object renderer (AI SDK UI Object Generation) where relevant
- [ ] Vitest tests for schema adherence (positive/negative cases)
- [ ] Write ADR(s)/Spec(s) for structured outputs strategy

## Working instructions (mandatory)

- Prefer schema-first design; return concise objects; avoid overfetching.
- Redact sensitive fields in errors.

## File & module targets

- `frontend/src/lib/schemas/*.ts` (Zod schemas)
- `frontend/src/app/api/*/route.ts` (integrated `Output.object`)
- `frontend/src/app/*` UI pages using Object Generation (optional)
- `frontend/tests/structured-outputs/*.test.ts`

## Legacy mapping (delete later)

- Remove ad-hoc JSON post-processing in Python once structured outputs validated in Next.js.
