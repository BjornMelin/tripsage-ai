# Prompt: Optional Adoption of Vercel AI Gateway (Unified Endpoint)

Executive summary

- Goal: Optionally route all provider calls through AI Gateway for unified API, spend monitoring, retries, and attribution; keep this isolated for a feature flag rollout.

Custom persona

- You are “AI SDK Migrator (Gateway)”. You ensure zero-regression by feature flagging.

Docs & references

- AI Gateway docs: <https://vercel.com/docs/ai-gateway>
- App Attribution: <https://vercel.com/docs/ai-gateway/app-attribution>
- exa.crawling_exa the Gateway docs; firecrawl_scrape app attribution
- zen.planner; zen.consensus for adopting Gateway (≥ 9.0/10); zen.secaudit for security
- zen.codereview

Plan (overview)

1) Add feature flag `ENABLE_AI_GATEWAY`
2) If enabled, configure AI SDK to point to Gateway endpoint; include app attribution headers
3) Vitest tests: config-based routing switch

Checklist (mark off; add notes under each)

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

Working instructions (mandatory)

- Check off tasks only after Vitest/biome/tsc are clean.
- Add “Notes” per task; address or log.

Legacy mapping (delete later)

- Any Python-side proxying or gateways
- Use exa.crawling_exa on Gateway docs; exa.get_code_context_exa for provider integration examples.
- Use zen.consensus to decide toggling criteria and rollout plan (≥ 9.0/10).
- Document Gateway adoption decision in `docs/adrs/` and author a Spec in `docs/specs/` outlining config, flags, migration path, and rollback.

Process flow (required)

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
