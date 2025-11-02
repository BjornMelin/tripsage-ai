# Prompt: Gateway Default vs BYOK Direct Routing Validation

## Executive summary

- Goal: Validate that non-BYOK traffic routes via Vercel AI Gateway and BYOK uses direct provider clients server-side. Add targeted tests and telemetry checks.
- Outcome: Verified routing behavior, budget config via Gateway, and zero key leakage.

## Custom persona

- You are “AI SDK Migrator (Routing Validation)”. You ensure routing correctness and observability.
  - Library-first, final-only; remove legacy once validated.
  - Autonomously use tools: zen.planner, zen.thinkdeep, zen.analyze, zen.consensus, zen.secaudit, zen.challenge, zen.codereview; exa.web_search_exa, exa.crawling_exa, exa.get_code_context_exa; firecrawl_scrape for single pages.
  - Success criteria: Default = Gateway, BYOK = direct provider; tests proving both; no key leakage; minimal telemetry attributes.

## Tools to use (invoke explicitly)

- exa.web_search_exa: find Gateway routing patterns and best practices
- exa.crawling_exa: fetch Gateway docs
- firecrawl_scrape: single-page extractions for quick reference
- exa.get_code_context_exa: provider registry examples and model slug usage
- zen.planner: plan steps (single in_progress)
- zen.thinkdeep + zen.analyze: weigh routing paths and edge cases
- zen.consensus: finalize routing decision criteria (≥ 9.0/10)
- zen.secaudit: verify secret handling and header policies
- zen.challenge: challenge any lock-in or latency assumptions
- zen.codereview: final pass

## Docs & references

- AI Gateway: <https://vercel.com/docs/ai-gateway>
- Providers & Models: <https://ai-sdk.dev/docs/foundations/providers-and-models>

## Plan (overview)

1) Ensure provider registry factory returns Gateway-backed client by default
2) Ensure BYOK path constructs a direct provider client with `apiKey: userKey` (server-only)
3) Add tests that simulate user with/without BYOK and assert chosen path
4) Add minimal OTel attributes (provider/model) without PII

## Checklist (mark off; add notes under each)

- [ ] Registry default path = Gateway; BYOK path = direct provider
  - Notes:
- [ ] Tests: route/unit cover both paths and prevent key leakage
  - Notes:
- [ ] OTel attributes present (best-effort), no PII in logs
  - Notes:
- [ ] Codereview + finalize
  - Notes:

## Working instructions (mandatory)

- Keep secret handling server-only; never expose keys to client bundles.
- Keep routing logic centralized; avoid duplicating per-route provider creation.

## File & module targets

- `frontend/src/lib/providers/registry.ts` (routing decisions)
- `frontend/src/app/api/chat/stream/route.ts` (ensures registry usage)
- `frontend/tests/providers-routing/*.test.ts` (Gateway vs BYOK tests)

## Legacy mapping (delete later)

- Remove Python provider wrappers and proxies once routing validated:
  - `tripsage_core/services/external_apis/llm_providers.py`
  - Any FastAPI gateway/proxy shims used for LLM calls

## Process flow (required)

1) Research: Gateway docs + provider setup
2) Plan: define test cases and attributes to assert
3) Implement: registry checks and tests
4) Review: zen.codereview; fix; finalize

## Testing requirements

- Unit/integration tests for registry and chat route verifying Gateway vs BYOK path
- Verify no keys in client-visible responses
