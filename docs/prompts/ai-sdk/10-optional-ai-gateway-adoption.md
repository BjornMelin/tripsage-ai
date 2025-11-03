# Prompt: Optional Adoption of Vercel AI Gateway (Unified Endpoint)

## Executive summary

- Goal: Optionally route all provider calls through AI Gateway for unified API, spend monitoring, retries, and attribution; keep this isolated for a feature flag rollout.

## Custom persona

- You are “AI SDK Migrator (Gateway)”. You ensure zero-regression by feature flagging.
  - Library-first, final-only; remove legacy once validated.
  - Autonomously use tools: zen.planner, zen.thinkdeep, zen.analyze, zen.consensus, zen.secaudit, zen.challenge, zen.codereview; exa.web_search_exa, exa.crawling_exa, exa.get_code_context_exa; firecrawl_scrape for single pages.
  - Success criteria: Gateway default for non-BYOK; budgets and fallbacks configured; tests for routing; no key leaks; app attribution when needed.

## Docs & references

- AI Gateway docs: <https://vercel.com/docs/ai-gateway>
- App Attribution: <https://vercel.com/docs/ai-gateway/app-attribution>
- Providers & Models: <https://v6.ai-sdk.dev/docs/foundations/providers-and-models>
- exa.crawling_exa the Gateway docs; firecrawl_scrape app attribution
- zen.planner; zen.consensus for adopting Gateway (≥ 9.0/10); zen.secaudit for security
- zen.codereview

## Plan (overview)

1) Add feature flag `ENABLE_AI_GATEWAY`
2) If enabled, configure AI SDK to point to Gateway endpoint; include app attribution headers (where appropriate)
3) Vitest tests: config-based routing switch
4) Configure budgets and provider order in Gateway dashboard; document order
5) Add minimal telemetry attribute (provider/model) without PII

## Checklist (mark off; add notes under each)

- [ ] Add `ENABLE_AI_GATEWAY` feature flag to settings
  - Notes:
- [ ] Configure provider creation to use Gateway endpoint when flag enabled
  - Notes:
- [ ] Ensure app attribution headers are passed via Gateway
  - Notes:
- [ ] Vitest tests toggling flag and asserting provider base URL
  - Notes:
- [ ] Write ADR(s) and Spec(s) for Gateway adoption plan
  - Notes:
- [ ] Configure budgets and provider order in Gateway dashboard (document slugs)
  - Notes:
- [ ] Add telemetry attributes for provider/model (OTel spans)
  - Notes:

### Augmented checklist (compatibility & safety)

- [ ] Keep BYOK/provider registry intact; route via Gateway post-resolution
- [ ] Never expose keys client-side; Gateway config SSR-only
- [ ] Map errors consistently between direct provider and Gateway paths

## Working instructions (mandatory)

- Check off tasks only after Vitest/biome/tsc are clean.
- Add “Notes” per task; address or log.

## File & module targets

- `frontend/lib/providers/registry.ts` (Gateway base URL injection + feature flag)
- `frontend/lib/settings.ts` (feature flag, provider order)
- `frontend/tests/providers-gateway/*.test.ts` (toggle tests)

## Legacy mapping (delete later)

- Remove Python gateway/proxy code and any legacy app attribution code once Next.js Gateway integration is validated.
- Any Python-side proxying or gateways
- Use exa.crawling_exa on Gateway docs; exa.get_code_context_exa for provider integration examples.
- Use zen.consensus to decide toggling criteria and rollout plan (≥ 9.0/10).
- Document Gateway adoption decision in `docs/adrs/` and author a Spec in `docs/specs/` outlining config, flags, migration path, and rollback.

## Process flow (required)

1) Research: exa.web_search_exa → exa.crawling_exa → firecrawl_scrape → exa.get_code_context_exa on Gateway usage.
2) Plan: zen.planner; define atomic tasks.
3) Deep design: zen.thinkdeep + zen.analyze on rollout criteria and fallbacks.
4) Decide: zen.consensus (≥ 9.0/10);
5) Draft docs: ADR(s)/Spec(s) for feature flag and migration.
6) Security review: zen.secaudit (key handling, headers).
7) Implement: code + tests; keep Biome/tsc clean.
8) Challenge: zen.challenge assumptions.
9) Review: zen.codereview; fix; rerun checks.
10) Finalize docs: update ADR/Spec with deltas.

---

## Final Alignment with TripSage Migration Plan (Next.js 16 + AI SDK v6)

- Core decisions impacting Gateway:
  - Default routing via Vercel AI Gateway for non‑BYOK; BYOK remains direct provider path.
  - Configure budgets, provider ordering, and fallbacks in Gateway instead of code logic.

- Implementation checklist delta:
  - Centralize model slugs; SSR-only configuration; ensure registry cooperates with Gateway defaults.
  - Add OTel attributes to identify model/provider choice without PII.

- References:
  - AI Gateway: <https://vercel.com/docs/ai-gateway>

Verification

- Gateway on by default (except BYOK); logs/traces confirm path; toggling does not break chat streaming.
