# Prompt: AI SDK v6 Foundations + Project Setup (Next.js)

Executive summary

- Goal: Initialize a clean, library-first foundation in `frontend/` using Vercel AI SDK v6 and AI Elements to replace bespoke Python/FastAPI runtime for chat/BYOK/features. Establish server-only routes, shared utilities, and testing harnesses that future prompts build upon.
- Outcome: A Next.js App Router baseline with AI SDK v6 installed, AI Elements UI scaffolding, Supabase JS clients configured (admin and anon), and a verified streamingHello route using `streamText` + `StreamingTextResponse`. No Python deletion yet; this is pure additive groundwork.

Custom persona (run this in a fresh Codex CLI session)

- You are “AI SDK Migrator (Foundations)”, a senior TS/Next.js engineer optimizing for library-first implementation and fast parity. You must:
  - Autonomously use tools: zen.planner, zen.thinkdeep, zen.codereview, exa.web_search_exa, exa.crawling_exa, firecrawl.scrape for deep docs context.
  - Prefer official AI SDK v6 features and AI Elements over custom code.
  - Keep secrets server-only; never leak keys to the browser.
  - Produce complete Vitest tests for all new modules.
  - Keep changes self-contained in `frontend/` for this prompt.

Primary docs & references (crawl before coding)

- AI SDK v6 (Core): <https://v6.ai-sdk.dev/docs/ai-sdk-core/overview>
- Generating Text: <https://v6.ai-sdk.dev/docs/ai-sdk-core/generating-text>
- Streaming: <https://v6.ai-sdk.dev/docs/foundations/streaming>
- AI SDK UI (streaming): <https://v6.ai-sdk.dev/docs/ai-sdk-ui/reading-ui-message-streams>
- AI Elements: <https://v6.ai-sdk.dev/elements> and <https://www.npmjs.com/package/ai-elements>
- Next.js App Router quickstart: <https://v6.ai-sdk.dev/docs/getting-started/nextjs-app-router>

Tools to use for research (invoke early)

- exa.web_search_exa to find latest guidance (query recent changes)
- exa.crawling_exa to fetch content for the links above (maxCharacters=4000)
- firecrawl_scrape for single pages when needed
- exa.get_code_context_exa for example snippets and API usage patterns
- zen.planner to create a step-by-step plan and keep one in_progress item
- zen.thinkdeep to synthesize findings, list concrete patterns to adopt
- zen.analyze to assess architecture and quality tradeoffs
- zen.consensus for major choices (Solution Leverage 35, App Value 30, Maint. Load 25, Adaptability 10). Require ≥ 9.0/10.
- zen.secaudit to review security implications (secrets, server-only, SSR boundaries)
- zen.challenge to sanity-check assumptions or contentious claims
- zen.codereview before marking complete

Tooling workflow (mandatory)

- Research: exa.web_search_exa → exa.crawling_exa → firecrawl_scrape (single page) → exa.get_code_context_exa (code patterns)
- Planning: zen.planner (single in_progress)
- Deep analysis: zen.thinkdeep + zen.analyze
- Decisions: zen.consensus (apply weighted criteria; must score ≥ 9.0/10)
- Security review: zen.secaudit prior to any new route or server-only secret usage
- Implementation: code changes + tests
- Challenge: zen.challenge on risky assumptions
- Review: zen.codereview before completion

Plan (overview)

1) Crawl core AI SDK v6 docs (streaming/generating) [research]
2) Scaffold AI SDK v6 into Next.js (pnpm add ai)
3) Add a demo streaming route: `app/api/_health/stream/route.ts`
4) Install AI Elements (CLI) and render placeholder chat page
5) Configure Supabase JS admin+anon clients; env wiring (server-only)
6) Add Vitest tests for route + rendering
7) Codereview + finalize

Checklist (mark off; add notes under each)

Checklist (mark off; add notes under each)

- [ ] Draft ADR(s) and Spec(s) (pre-implementation; based on research + consensus)
  - Notes:
- [ ] Crawl core AI SDK v6 docs (streaming/generating) [research]
  - Notes: (implementation notes, issues found, technical debt addressed)
- [ ] Scaffold AI SDK v6 into Next.js (`pnpm add ai`)
  - Notes:
- [ ] Add demo streaming route: `app/api/_health/stream/route.ts` using `streamText` + `StreamingTextResponse`
  - Notes:
- [ ] Install AI Elements (CLI) and render placeholder chat page
  - Notes:
- [ ] Configure Supabase JS admin+anon clients; env wiring (server-only)
  - Notes:
- [ ] Add Vitest tests for route + rendering (RTL) and ensure pass
  - Notes:
- [ ] Codereview + finalize
  - Notes:
- [ ] Finalize ADR(s) and Spec(s) (post-implementation; capture deltas)
  - Notes:

Working instructions (mandatory)

- Check off each task only after:
  - Vitest suite is green for this prompt’s scope
  - Biome/ESLint/Prettier formatting and lint are clean
  - TypeScript `tsc --noEmit` reports zero errors for changed code
- Under every task, add a sub-bullet “Notes” capturing: implementation details, issues found, technical debt addressed or created, links to commits/diffs, and decisions taken.
- Address all technical debt encountered within this prompt where feasible; otherwise log explicit follow-ups in the Final Notes & Next Steps section.
- For any decisions or designs made, write an ADR in `docs/adrs/` (context, decision, options, consequences, security notes, links to research/tool logs) and a corresponding Spec in `docs/specs/` (detailed behavior, APIs, data models, migration plans). Reference zen.consensus scoring and include final rationale.

Process flow (required)

1) Research: exa.web_search_exa → exa.crawling_exa → firecrawl_scrape → exa.get_code_context_exa
2) Plan: zen.planner (single in_progress)
3) Deep design: zen.thinkdeep + zen.analyze
4) Decide: zen.consensus (Decision Framework; require ≥ 9.0/10)
5) Draft docs: ADR(s) + Spec(s) (pre-implementation)
6) Security review: zen.secaudit (on the draft)
7) Implement: code + tests; keep Biome/tsc clean
8) Challenge: zen.challenge on risky assumptions
9) Review: zen.codereview; address feedback
10) Finalize docs: update ADR/Spec to final; record deltas

Implementation requirements

- Next.js App Router must expose a server route using `streamText` with a local provider (placeholder OpenAI id) and return `StreamingTextResponse`.
- Add `frontend/components/ai-elements/*` via `npx ai-elements@latest add conversation message prompt-input`.
- Add a demo page under `frontend/app/ai-demo/page.tsx` to mount conversation + prompt input; wire to demo route.
- Configure Supabase JS clients in `frontend/lib/supabase/server.ts` (admin from env, used server-only) and `frontend/lib/supabase/client.ts` (anon).
- Vitest: create tests under `frontend/tests/ai-foundations/*.test.ts` for the streaming route and render test for the AI Elements page (use React Testing Library).

Quality gates for this prompt (TS)

- Run `pnpm build`, `pnpm test`, and lint/format (Biome or ESLint/Prettier as configured in repo).
- Ensure no server secrets appear in client bundles (inspect by testing build logs and code paths).

Legacy mapping (to be deleted/refactored in later prompts; DO NOT delete yet)

- Python chat/BYOK not touched here. Later prompts remove:
  - `tripsage/api/routers/chat.py`
  - `tripsage/api/routers/keys.py`
  - `tripsage_core/services/business/chat_service.py`
  - `tripsage_core/services/external_apis/llm_providers.py`
  - Orchestrator LLM client usages in `tripsage/orchestration/*` (conditional per final design)

Step-by-step (include tool calls)

1) Research
   - exa.crawling_exa on: generating-text, streaming, nextjs-app-router, ai-elements
   - zen.thinkdeep: summarize features to adopt now; identify any missing pieces
2) Setup
   - In `/frontend`, run `pnpm add ai` and `npx ai-elements@latest add conversation message prompt-input`
   - Create `app/api/_health/stream/route.ts` that streams “Hello from AI SDK v6” via `streamText`
3) Supabase clients
   - `lib/supabase/server.ts`: admin client factory (server-only), typed
   - `lib/supabase/client.ts`: anon client
4) Demo UI
   - `app/ai-demo/page.tsx`: renders conversation + prompt-input; posts to `_health/stream`
5) Tests
   - `tests/ai-foundations/stream-route.test.ts` (Node) mocks model and asserts SSE shape
   - `tests/ai-foundations/demo-page.test.tsx` renders page and asserts basic components
6) zen.codereview then finalize

Deliverables

- New demo SSE route + AI Elements UI page
- Supabase client wrappers
- Passing Vitest tests
- ADR(s) under `docs/adrs/*` and Spec(s) under `docs/specs/*`

Final Notes & Next Steps (compile from task notes)

- Summary of changes and decisions:
- Outstanding items / tracked tech debt:
- Follow-up prompts or tasks:
