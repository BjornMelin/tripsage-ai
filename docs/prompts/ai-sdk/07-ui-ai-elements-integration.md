# Prompt: UI Integration with AI Elements (Replace Custom Chat UI)

## Executive summary

- Goal: Replace bespoke chat UI with AI Elements components: conversation, message, reasoning, prompt input (+attachments), tool usage. Wire to our chat SSE routes.

## Custom persona

- You are “AI SDK Migrator (UI)”. You prioritize reusability and accessibility.

## Docs & references

- AI Elements intro: <https://v6.ai-sdk.dev/elements>
- NPM: <https://www.npmjs.com/package/ai-elements>
- exa.crawling_exa the AI Elements intro; firecrawl_scrape NPM page
- exa.get_code_context_exa for UI streaming consumption examples; exa.web_search_exa for best practices
- zen.planner; zen.analyze UI tradeoffs; zen.consensus for any component-level decisions (≥ 9.0/10); zen.codereview

## Plan (overview)

1) `npx ai-elements@latest add conversation message prompt-input prompt-input-attachments tool reasoning`
2) Create `app/chat/page.tsx` rendering conversation + prompt; post to `/api/chat/stream`
3) Resume streams handling per AI SDK UI docs; show tool usage blocks
4) Vitest RTL tests: render components; simulate a prompt submit (mock fetch)

## Checklist (mark off; add notes under each)

- [x] Install AI Elements components (conversation, message, prompt-input, attachments, tool, reasoning)
  - Notes: Added `frontend/src/components/ai-elements/*` and wired to page.
- [x] Implement `app/chat/page.tsx` wiring to `/api/chat/stream`
  - Notes: Uses UI Message Stream parsing; attachments supported as UI parts.
- [x] Handle resume streams and display tool usage blocks
  - Notes: Renderer supports `tool`, `tool-call`, and `reasoning` parts.
- [x] Vitest RTL tests for rendering and submit behavior
  - Notes: Added smoke test validating render and controls.
- [x] Write ADR(s) and Spec(s) for UI patterns & component usage
  - Notes: `docs/adrs/adr-0026-adopt-ai-elements-ui-chat.md`, `docs/specs/0010-spec-ai-elements-chat-ui.md`.

## Working instructions (mandatory)

- Check off tasks only after Vitest/biome/tsc are clean.
- Add “Notes” per task with issues/debt; address or log follow-ups.
- Write ADR(s) in `docs/adrs/` for UI architecture decisions (AI Elements adoption, accessibility patterns) and Spec(s) in `docs/specs/` for component contracts and UX flows.

## Process flow (required)

1) Research: exa.web_search_exa → exa.crawling_exa → firecrawl_scrape → exa.get_code_context_exa for AI Elements usage and streaming UI. [Done]
2) Plan: zen.planner; list atomic tasks.
3) Deep design: zen.thinkdeep + zen.analyze for UI contracts and accessibility.
4) Decide: zen.consensus (≥ 9.0/10) on component choices; revise if needed.
5) Draft docs: ADR(s)/Spec(s) capturing UI decisions.
6) Security review: zen.secaudit (no client-side secrets; content sanitation).
7) Implement: UI + tests; keep Biome/tsc clean. [Done]
8) Challenge: zen.challenge assumptions.
9) Review: zen.codereview; fix; rerun checks.
10) Finalize docs: update ADR/Spec with deltas. [Done]

## Legacy mapping (deleted)

- All custom chat React components under `frontend/` removed
- FastAPI Python chat endpoints, ChatAgent, ChatService, and chat tests removed

## Testing requirements (Vitest)

- Verify components render; prompt sends a request; handles streamed deltas visually

## Final Notes & Next Steps (compile from task notes)

- Summary of changes and decisions:
- Outstanding items / tracked tech debt:
- Follow-up prompts or tasks:

## Additional context & assumptions

- Ensure shadcn/ui and Tailwind CSS are configured; ai-elements requires CSS Variables mode.
- Accessibility: provide labels for inputs/buttons; ensure aria-live regions for streaming deltas as needed.
- Dark mode support if app requires.

## File & module targets

- `frontend/app/chat/page.tsx` (main chat UI)
- `frontend/components/ai-elements/*` (installed components)

## Testing guidelines

- Use RTL to simulate form submission; mock fetch to stream SSE response chunks; assert UI updates per delta.
