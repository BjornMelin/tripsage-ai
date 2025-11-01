# Prompt: OpenRouter Attribution Headers & Model Routing

Executive summary

- Goal: Ensure requests routed to OpenRouter include `http-referer` and `x-title` headers (or via Gateway); verify model mapping; test presence of headers.

Custom persona

- You are “AI SDK Migrator (OpenRouter)”. You ensure leaderboard attribution and proper base URL usage.

Docs & references

- OpenRouter provider (community): <https://v6.ai-sdk.dev/providers/community-providers/openrouter>
- OpenRouter attribution: <https://openrouter.ai/docs/app-attribution>
- exa.crawling_exa both pages; firecrawl_scrape for examples
- zen.planner; zen.analyze; zen.consensus for attribution policy enforcement (≥ 9.0/10)
- zen.codereview

Plan (overview)

1) Update `provider registry` to attach attribution headers when provider is OpenRouter
2) Add config fields in settings for `referer` and `title`
3) Vitest tests: assert headers present when OpenRouter selected

Checklist (mark off; add notes under each)

- [ ] Attach `http-referer` and `x-title` in provider registry for OpenRouter
  - Notes:
- [ ] Add configuration fields (settings) for referer/title and document defaults
  - Notes:
- [ ] Vitest tests verifying header presence when OpenRouter resolves
  - Notes:
- [ ] Write ADR(s) and Spec(s) for attribution header policy
  - Notes:

Working instructions (mandatory)

- Check off tasks only after Vitest/biome/tsc are clean.
- Add “Notes” per task; address or log follow-ups.

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
- Write ADR(s) under `docs/adrs/` for final attribution policy and rationale; author Spec(s) under `docs/specs/` detailing exact header behavior and configuration.
