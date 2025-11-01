# Spec 0008: AI SDK v6 Foundations (Next.js)

## Scope

- Add a server-only streaming route using AI SDK `streamText` and return a UI Message Stream response.
- Scaffold AI Elements chat UI primitives and a simple demo page.
- Keep changes contained to `frontend/`.

## APIs & Routes

- POST `src/app/api/_health/stream/route.ts`
  - Request: optional JSON `{ prompt?: string }` (ignored in demo)
  - Response: `toUIMessageStreamResponse()` from `streamText` with placeholder model id `openai/gpt-4o`
  - Max duration: 30s

## UI Components

- AI Elements installed via CLI:
  - `src/components/ai-elements/conversation.tsx`
  - `src/components/ai-elements/message.tsx`
  - `src/components/ai-elements/prompt-input.tsx`
- Demo page `src/app/ai-demo/page.tsx` renders Conversation and PromptInput.

## Supabase Clients

- Existing SSR helpers remain in `src/lib/supabase/*`. No changes required in this prompt.

## Testing

- Unit tests (Vitest):
  - `frontend/tests/ai-foundations/stream-route.test.ts` mocks `ai.streamText` and asserts SSE response headers
  - `frontend/tests/ai-foundations/demo-page.test.tsx` renders the demo page and asserts base controls

## Non-Functional

- Linting: Ensure no new lint errors in added files; acknowledge 3rd-party component rules may differ.
- Build: `pnpm build` must succeed with required public env set (e.g., `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`).
- Security: No server secrets referenced from client components; route emits no sensitive details.

## Out of Scope

- BYOK endpoints, provider registry, and tool-calling (covered by later prompts).
- Deleting Python chat code (future prompt).
