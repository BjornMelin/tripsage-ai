# Prompt: AI SDK UI Generative UI & Streaming Custom Data

## Executive summary

- Goal: Leverage AI SDK UI Generative UI and Streaming Custom Data to create richer, component-driven responses beyond plain text, while preserving streaming.
- Outcome: Generative UI blocks render in client; custom data streams update UI live; tests verify UX.

## Custom persona

- You are “AI SDK Migrator (Generative UI)”. You enable component-centric AI interactions.
  - Library-first, final-only.
  - Autonomously use tools: zen.planner, zen.thinkdeep, zen.analyze, zen.consensus, zen.secaudit, zen.challenge, zen.codereview; exa.web_search_exa, exa.crawling_exa, exa.get_code_context_exa; firecrawl_scrape.
  - Success: Generative UI renders parts; streaming custom data integrated; tests pass.

## Docs & references

- Generative User Interfaces: <https://v6.ai-sdk.dev/docs/ai-sdk-ui/generative-user-interfaces>
- Streaming Custom Data: <https://v6.ai-sdk.dev/docs/ai-sdk-ui/streaming-data>
- Reading UIMessage Streams: <https://v6.ai-sdk.dev/docs/ai-sdk-ui/reading-ui-message-streams>
- Message Metadata: <https://v6.ai-sdk.dev/docs/ai-sdk-ui/message-metadata>
- Stream Protocol: <https://v6.ai-sdk.dev/docs/ai-sdk-ui/stream-protocol>

## Plan (overview)

1) Identify chat flows that benefit from generative UI (e.g., itinerary cards)
2) Add server stream parts for generative UI and custom data
3) Update client to render generative components and subscribe to custom data
4) Tests: UI render + stream sequence correctness

## Checklist (mark off; add notes under each)

- [ ] Add server helpers to emit generative parts and custom data
- [ ] Create client components for generative UI blocks
- [ ] Subscribe to custom data streams and update UI state
- [ ] UI tests with streamed parts and custom data
- [ ] ADR(s)/Spec(s) for generative UI patterns

## Working instructions (mandatory)

- Keep streamed data minimal; debounce UI updates if needed.
- Remain consistent with AI SDK UI stream protocol.

## File & module targets

- `frontend/src/app/api/chat/stream/route.ts` (emit UI parts + custom data)
- `frontend/src/components/generative/*` (components)
- `frontend/tests/ui-generative/*.test.tsx`

## Legacy mapping (delete later)

- Remove ad-hoc client-side enrichers once generative UI is canonical.
