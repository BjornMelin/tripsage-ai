# Prompt: Vitest & E2E Testing for AI SDK v6 Routes/Modules

## Executive summary

- Goal: Add comprehensive Vitest suite for provider registry, BYOK routes, chat SSE, tools/MCP, and memory. Include integration tests with provider/Supabase mocks and UI render tests.

## Custom persona

- You are “AI SDK Migrator (Testing)”. You ensure high coverage with fast feedback.

## Plan (overview)

1) Setup Vitest config if not present; include jsdom for UI tests
2) Unit tests:
   - provider registry resolution precedence + OpenRouter headers
   - token budgeting clamp
   - BYOK RPC wrappers (mock Supabase)
   - tools schema/execute
3) Integration tests:
   - chat SSE event ordering + final usage
   - /api/keys validate route (provider mocked)
   - memory read/write through chat endpoints
4) UI tests (RTL): AI Elements Chat page renders + prompt triggers fetch

## Checklist (mark off; add notes under each)

- [ ] Configure Vitest + jsdom for UI tests
  - Notes:
- [ ] Unit tests: registry precedence + OpenRouter headers
  - Notes:
- [ ] Unit tests: token clamping
  - Notes:
- [ ] Unit tests: BYOK RPC wrappers
  - Notes:
- [ ] Unit tests: tools schema/execute
  - Notes:
- [x] Integration: chat SSE ordering + usage (smoke-level; clamp/no-output + metadata via route unit tests)
  - Notes:
  - Include auth (401), rate-limit (429), and tool-call interleave
- [ ] Integration: /api/keys validate (provider mocked)
  - Notes:
- [ ] Integration: memory read/write via chat
  - Notes:
- [ ] UI: AI Elements page render + prompt submit
  - Notes:
- [ ] Write ADR(s) and Spec(s) for testing strategy and coverage
  - Notes:

### Augmented checklist (attachments, resume, persistence)

- [x] Route tests for attachments mapping (validation errors for non-image)
- [ ] Resume behavior (id reuse) happy path test
- [x] Sessions/messages CRUD tests (create/list/get/delete; message insert)

## Working instructions (mandatory)

- Check off tasks only after Vitest/biome/tsc are clean.
- Add “Notes” per task; address or log.

## Legacy mapping

- Mark Python tests covering these features for deletion in decommission prompt
- Use zen.planner to track testing subtasks.
- Use exa.get_code_context_exa for testing patterns and examples; exa.web_search_exa for latest guidance.
- Use zen.analyze to assess gaps in coverage; zen.challenge for flaky or brittle tests.
- Use zen.consensus for key testing strategy decisions (≥ 9.0/10).
- Write ADR(s) in `docs/adrs/` for testing strategy, coverage targets, and mocking patterns; author Spec(s) in `docs/specs/` with test plans and fixtures.

## Process flow (required)

1) Research: exa.web_search_exa → exa.crawling_exa → firecrawl_scrape → exa.get_code_context_exa for Vitest/MSW/RTL best practices.
2) Plan: zen.planner; define atomic test tasks.
3) Deep design: zen.thinkdeep + zen.analyze for coverage plan, mocking, and performance.
4) Decide: zen.consensus (≥ 9.0/10) on test strategy.
5) Draft docs: ADR(s)/Spec(s) for test strategy.
6) Security review: zen.secaudit (ensure tests don’t leak secrets).
7) Implement: tests; ensure Biome/tsc clean.
8) Challenge: zen.challenge for flaky tests.
9) Review: zen.codereview; fix; rerun.
10) Finalize docs: update ADR/Spec with deltas.

## Additional context & assumptions

- Prefer MSW (Mock Service Worker) to mock Next.js route fetches in integration tests.
- Mock Supabase JS via dependency injection or module mocks; avoid network.
- For streaming tests, simulate server-sent chunks and assert UI consumption.
- Coverage targets: ensure each module has unit tests and at least one integration path through /api/chat and /api/keys.
