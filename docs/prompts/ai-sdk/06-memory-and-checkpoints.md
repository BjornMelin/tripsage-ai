# Prompt: Memory & Checkpoints (Supabase-first; optional LangGraph JS)

## Executive summary

- Goal: Port session/message persistence and context assembly to Supabase JS in Next.js. If advanced multi-step orchestration is required, adopt LangGraph JS with Supabase-backed persistence; otherwise rely on AI SDK agents.

## Custom persona

- You are “AI SDK Migrator (Memory)”. You keep persistence simple, secure, and cost-aware.

## Docs & references

- LangGraph JS overview/persistence (optional): <https://docs.langchain.com/oss/javascript/langgraph/overview> and /persistence
- AI SDK agents (workflows/loop control): <https://v6.ai-sdk.dev/docs/agents>
- exa.crawling_exa for both; firecrawl_scrape for specific sections
- exa.get_code_context_exa for examples of agents/persistence
- zen.planner; zen.thinkdeep + zen.analyze; zen.consensus for whether to adopt LangGraph JS (≥ 9.0/10)
- zen.secaudit for data handling; zen.challenge assumptions; zen.codereview before completion

## Plan (overview)

1) `frontend/lib/memory/index.ts`:
   - addMessage, getMessages(sessionId, limit), getUserContext, sanitize content, select by token budget
2) Update chat routes to read/write memory as needed
3) Optional: integrate LangGraph JS for checkpoints if workflows require it
4) Vitest tests: memory read/write; token-window selection

## Checklist (mark off; add notes under each)

- [ ] Implement `frontend/lib/memory/index.ts` (addMessage/getMessages/getUserContext)
  - Notes:
- [ ] Sanitize content and select window by token budget
  - Notes:
- [ ] Update chat routes to read/write memory
  - Notes:
- [ ] (Optional) Integrate LangGraph JS checkpoints if required
  - Notes:
- [ ] Vitest tests for memory CRUD + token window selection
  - Notes:
- [ ] Write ADR(s) and Spec(s) for memory/checkpointing strategy
  - Notes:

## Working instructions (mandatory)

- Check off tasks only after Vitest/biome/tsc are clean.
- Add “Notes” for impl details, issues, and debt; address or log.
- Write ADR(s) in `docs/adrs/` for persistence/design choices (Supabase vs LangGraph JS); Spec(s) in `docs/specs/` for data schemas, APIs, and migration.

## Process flow (required)

1) Research: exa.web_search_exa → exa.crawling_exa → firecrawl_scrape → exa.get_code_context_exa for AI SDK agents and LangGraph JS persistence.
2) Plan: zen.planner; define atomic tasks.
3) Deep design: zen.thinkdeep + zen.analyze to choose Supabase-only vs LangGraph JS.
4) Decide: zen.consensus (≥ 9.0/10). Revise if needed.
5) Draft docs: ADR(s)/Spec(s) for persistence + schemas.
6) Security review: zen.secaudit (RLS, data exposure).
7) Implement: code + tests; keep Biome/tsc clean.
8) Challenge: zen.challenge assumptions.
9) Review: zen.codereview; fix; rerun checks.
10) Finalize docs: update ADR/Spec with deltas.

## Legacy mapping (delete later)

- `tripsage_core/services/business/chat_service.py` memory methods
- Orchestrator checkpoint service in Python if replaced by LangGraph JS

## Testing requirements (Vitest)

- Unit tests for memory CRUD; integration to confirm chat routes store/load as expected

## Final Notes & Next Steps (compile from task notes)

- Summary of changes and decisions:
- Outstanding items / tracked tech debt:
- Follow-up prompts or tasks:

## Additional context & assumptions

- Suggested tables/columns (adjust to existing schema):
  - `chat_sessions(id, user_id, title, trip_id, created_at, updated_at, metadata jsonb)`
  - `chat_messages(id, session_id, role, content, created_at, metadata jsonb)`
- RLS: ensure `auth.uid() = user_id` policies remain enforced.
- Selection by token window: compute from newest to oldest until budget is met; always include current user message.

## File & module targets

- `frontend/lib/memory/index.ts` (CRUD + selectors)
- Optionally `frontend/lib/orchestration/langgraph.ts` if LangGraph JS is adopted

## Testing & mocking guidelines

- Seed data in test DB or mock Supabase client; assert that message windows respect token budgets and role ordering.
