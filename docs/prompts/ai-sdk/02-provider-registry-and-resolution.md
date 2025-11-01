# Prompt: Provider Registry & Resolution (OpenAI/Anthropic/xAI/OpenRouter)

Executive summary

- Goal: Implement a centralized provider registry in TS that resolves a user’s preferred provider+model using BYOK, sets OpenRouter attribution headers, and returns a ready-to-use AI SDK v6 model reference for downstream chat/routes. No model calls here—pure assembly.

Custom persona

- You are “AI SDK Migrator (Providers)”. You minimize custom glue and leverage first-party & community provider integrations. You never expose keys to clients.

Docs & references

- AI SDK Providers index: <https://v6.ai-sdk.dev/providers/ai-sdk-providers/openai> (OpenAI), <https://v6.ai-sdk.dev/providers/ai-sdk-providers/anthropic>, <https://v6.ai-sdk.dev/providers/ai-sdk-providers/xai>
- Community OpenRouter: <https://v6.ai-sdk.dev/providers/community-providers/openrouter> (attribution headers)
- AI Gateway (optional): <https://vercel.com/docs/ai-gateway> (app attribution headers accepted there too)

Tools to use

- exa.web_search_exa for latest provider capabilities
- exa.crawling_exa for provider docs (OpenAI, Anthropic, xAI, OpenRouter)
- firecrawl_scrape for single pages
- exa.get_code_context_exa for provider usage snippets with AI SDK v6
- zen.planner for tasks; zen.thinkdeep + zen.analyze for approach validation
- zen.consensus for provider order/selection, header policies (≥ 9.0/10)
- zen.secaudit (ensure no secrets leak, SSR only)
- zen.challenge to sanity-check assumptions
- zen.codereview before completion

Plan (overview)

1) Design `frontend/lib/providers/registry.ts` with functions:
   - `resolveProvider(userId: string, modelHint?: string)` returns `{ model, headers?, maxTokens? }`
   - Preference order: openai → openrouter → anthropic → xai (configurable)
2) Fetch BYOK via Supabase RPC wrappers; no keys returned to client
3) For OpenRouter, set `http-referer` and `x-title` when present in settings
4) Export narrow helpers to keep downstream code simple
5) Vitest tests: mock Supabase + providers; assert attribution headers and precedence

Checklist (mark off; add notes under each)

- [ ] Draft ADR(s) and Spec(s) (pre-implementation; research + consensus)
  - Notes:
- [ ] Implement `frontend/lib/providers/registry.ts`
  - Notes:
- [ ] `resolveProvider(userId, modelHint?)` returns `{ model, headers?, maxTokens? }`
  - Notes:
- [ ] Preference order: openai → openrouter → anthropic → xai (configurable)
  - Notes:
- [ ] Fetch BYOK via Supabase RPC wrappers; never expose keys client-side
  - Notes:
- [ ] Attach OpenRouter `http-referer` and `x-title` headers when applicable
  - Notes:
- [ ] Export narrow helpers to keep downstream code simple
  - Notes:
- [ ] Vitest tests: mock Supabase + providers; assert attribution headers and precedence
  - Notes:
- [ ] Finalize ADR(s) and Spec(s) for provider resolution policy
  - Notes:

Working instructions (mandatory)

- Check off tasks only after Vitest, Biome/ESLint/Prettier, and `tsc --noEmit` are clean.
- Under each task, record implementation “Notes”, issues, and tech debt addressed or follow-ups.
- Address encountered tech debt within this prompt or log in Final Notes.
- Write ADR(s) in `docs/adrs/` describing provider preference order, attribution rules, SSR boundaries, and secrets handling; add Spec(s) in `docs/specs/` defining returned shapes, mapping tables, and integration points.

Process flow (required)

1) Research: Use exa.web_search_exa → exa.crawling_exa → firecrawl_scrape → exa.get_code_context_exa to gather provider capabilities (OpenAI/Anthropic/xAI/OpenRouter). Summarize mapping and headers.
2) Plan: Use zen.planner with explicit atomic tasks (checkboxes).
3) Deep design: Run zen.thinkdeep + zen.analyze to define precedence order, returned shapes, attribution policy, and SSR boundaries.
4) Decide: Use zen.consensus (Decision Framework; require ≥ 9.0/10). Iterate if score falls short.
5) Draft docs: Author ADR(s) and Spec(s) recording provider registry design and integration.
6) Security review: Run zen.secaudit (secrets handling, no client exposure).
7) Implement: Build registry + tests; keep static checks clean.
8) Challenge: zen.challenge on assumptions (e.g., defaults, fallbacks).
9) Review: zen.codereview; fix; rerun tests.
10) Finalize docs: Update ADR/Spec with final decisions and deltas.

Implementation detail

- Use AI SDK provider factories; never store raw keys outside server route scope
- Accept a `modelHint` (e.g., "gpt-4o-mini"); map to provider-specific id when needed
- Return conservative `maxTokens` limit if known

Legacy mapping (delete later)

- `tripsage_core/services/external_apis/llm_providers.py` and any Python provider wrappers

Testing requirements (Vitest)

- Unit: returns OpenAI when user has openai key; falls back to OpenRouter with attribution headers; falls back to Anthropic/xAI as per config
- Ensure no secret material is ever included in return object

Final Notes & Next Steps (compile from task notes)

- Summary of changes and decisions:
- Outstanding items / tracked tech debt:
- Follow-up prompts or tasks:

Additional context & assumptions

- Supported services: `openai`, `openrouter`, `anthropic`, `xai`. Configurable preference order via a settings module.
- OpenRouter attribution headers: `http-referer` and `x-title` can be sourced from `OPENROUTER_REFERER` and `OPENROUTER_TITLE` (or project settings). Defaults should be sensible (e.g., site URL and app title).
- xAI base URL (if using OpenAI-compatible): `https://api.x.ai/v1` (or via Gateway). Feature-gate enablement.
- Returned object example:
  - `{ model, headers?: Record<string,string>, maxTokens?: number }`
  - `model` is the AI SDK v6 provider model reference, ready to be passed to `streamText`.

File & module targets

- `frontend/lib/providers/registry.ts` (implementation)
- `frontend/lib/providers/types.ts` (types for return shapes and settings)
- `frontend/lib/settings.ts` (provider selection order; attribution defaults)

Edge cases & decisions

- If user has multiple keys, select per preference order; if none, return an error (do not silently fallback to server key for end-user chat).
- Map `modelHint` to provider-specific models where necessary (document mapping table).
- For OpenRouter, ensure base URL is correctly set by provider implementation.

Testing & mocking guidelines

- Mock Supabase RPCs returning different provider keys to exercise precedence.
- Assert headers are attached only for OpenRouter.
- Ensure no raw secrets are returned from the registry.
