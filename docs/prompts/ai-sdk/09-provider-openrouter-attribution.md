# Prompt: OpenRouter Attribution Headers & Model Routing

## Executive summary

- Goal: Ensure requests routed to OpenRouter include `http-referer` and `x-title` headers (or via Gateway); verify model mapping; test presence of headers.

## Custom persona

- You are “AI SDK Migrator (OpenRouter)”. You ensure leaderboard attribution and proper base URL usage.

  - Library-first, final-only; remove legacy once validated.
  - Autonomously use tools: zen.planner, zen.thinkdeep, zen.analyze, zen.consensus, zen.secaudit, zen.challenge, zen.codereview; exa.web_search_exa, exa.crawling_exa, exa.get_code_context_exa; firecrawl_scrape for single pages.
  - Success criteria: Attribution headers applied server-side only, Gateway compatibility documented, unit tests pass; no header leaks to client.

## Docs & references

- OpenRouter provider (community): <https://v6.ai-sdk.dev/providers/community-providers/openrouter>
- OpenRouter attribution: <https://openrouter.ai/docs/app-attribution>
- AI SDK Providers & Models: <https://v6.ai-sdk.dev/docs/foundations/providers-and-models>
- AI Gateway: <https://vercel.com/docs/ai-gateway>
- exa.crawling_exa both pages; firecrawl_scrape for examples
- zen.planner; zen.analyze; zen.consensus for attribution policy enforcement (≥ 9.0/10)
- zen.codereview

## Plan (overview)

1) Update `provider registry` to attach attribution headers when provider is OpenRouter
2) Add config fields in settings for `referer` and `title`
3) Vitest tests: assert headers present when OpenRouter selected
4) Verify compatibility with Gateway (headers applied at Gateway layer where supported; else document direct path for BYOK)

## Checklist (mark off; add notes under each)

- [x] Attach `http-referer` and `x-title` in provider registry for OpenRouter
  - Notes: Implemented in `frontend/src/lib/providers/registry.ts` using `getProviderSettings()`; server-only
- [x] Add configuration fields (settings) for referer/title and document defaults
  - Notes: Implemented in `frontend/src/lib/settings.ts` via env vars `OPENROUTER_REFERER`, `OPENROUTER_TITLE`
- [x] Vitest tests verifying header presence when OpenRouter resolves
  - Notes: Added `frontend/src/lib/providers/__tests__/registry.test.ts` covering precedence and OpenRouter attribution headers; added case verifying no headers when env unset. Stream handler test asserts `provider` metadata.
- [x] Write ADR(s) and Spec(s) for attribution header policy
  - Notes: See ADR-0028 (`docs/adrs/adr-0028-provider-registry.md`) and Spec (`docs/specs/0012-provider-registry.md`) documenting attribution logic, server-only headers, and integration mapping.
- [x] Verify Gateway compatibility and document any differences
  - Notes: ADR updated (`docs/adrs/adr-0028-provider-registry.md`) with Gateway compatibility guidance: configure attribution in Gateway or continue direct OpenRouter with headers; headers remain server-only.

### Augmented checklist (provider registry + BYOK)

- [x] Provider registry resolves provider+model per-user (Supabase SSR)
- [x] Apply OpenRouter base URL and attribution headers only in server routes
- [ ] Fallback to default provider when user’s BYOK missing; record provider id in `messageMetadata`
- [x] Tests: mock SSR and verify header injection and fallback behavior
  - Notes: We do not fallback to a server-held key for end-user chat; registry throws when no BYOK is present (see SPEC/ADR). `provider` recorded in `messageMetadata`.

## Working instructions (mandatory)

- Check off tasks only after Vitest/biome/tsc are clean.
- Add “Notes” per task; address or log follow-ups.

## File & module targets

- `frontend/lib/providers/registry.ts` (inject attribution headers)
- `frontend/lib/settings.ts` (OpenRouter referer/title configuration)
- `frontend/tests/providers-openrouter/*.test.ts` (unit tests)

## Legacy mapping (delete later)

- Remove any Python‑side OpenRouter header glue once registry is validated; ensure the Next.js provider registry is canonical.

Legacy mapping (delete later)

- Python OpenRouter client glue
- Use exa.crawling_exa to fetch OpenRouter attribution docs; exa.get_code_context_exa for examples.
- Use zen.consensus to finalize attribution policy and defaults (≥ 9.0/10).

Process flow (required)

1) Research: exa.web_search_exa → exa.crawling_exa → firecrawl_scrape → exa.get_code_context_exa on OpenRouter attribution.
2) Plan: zen.planner; define atomic tasks.
3) Deep design: zen.thinkdeep + zen.analyze for header policy and defaults.
4) Decide: zen.consensus (≥ 9.0/10);
5) Draft docs: ADR(s)/Spec(s) describing attribution behavior.
6) Security review: zen.secaudit (headers contain no secrets).
7) Implement: code + tests; keep Biome/tsc clean.
8) Challenge: zen.challenge assumptions.
9) Review: zen.codereview; fix; rerun checks.
10) Finalize docs: update ADR/Spec with deltas.

---

## Final Alignment with TripSage Migration Plan (Next.js 16 + AI SDK v6)

- Core decisions impacting OpenRouter:
  - Provider registry applies attribution headers when selecting OpenRouter.
  - Default routing via AI Gateway where configured; ensure attribution remains compatible or is handled by Gateway when applicable.

- Implementation checklist delta:
  - Keep attribution header logic server‑side in the registry; never surface to client.
  - Add OTel attribute for `provider=openrouter` (no secrets).

- References:
  - AI SDK Providers/Models: <https://ai-sdk.dev/docs/foundations/providers-and-models>
  - AI Gateway: <https://vercel.com/docs/ai-gateway>
  - OpenRouter Attribution: <https://openrouter.ai/docs/app-attribution>

Verification

- Attribution applied correctly; client never sees headers; routing aligns with registry decisions.
