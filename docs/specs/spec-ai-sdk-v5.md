# Spec: AI SDK v5 Migration (Client + Route)

Owner: AI Feature Team
Status: In progress
Last updated: 2025-10-23

## Objective

Migrate the chat experience to AI SDK v5 using `@ai-sdk/react` and server routes returning UI message streams with tool support.

## Implementation Checklist

Client

- [x] Update `src/hooks/use-chat-ai.ts`:
  - [x] Import `useChat` from `@ai-sdk/react`.
  - [x] Replace `handleSubmit` with `sendMessage({ text })`.
  - [x] Map `message.parts` to text for legacy components (temporary adapter `messageToText`).
  - [ ] Render `parts` in UI where appropriate (tool parts like `tool-*`).

Server Route

- [x] Add/Update `app/api/chat/route.ts`:
  - [x] Use `streamText` with provider (e.g., `@ai-sdk/openai`) and convert UI messages to model messages.
  - [x] Return `result.toUIMessageStreamResponse()`.
  - [x] Example `confirm` tool added with `inputSchema` (Zod). Follow-up: add tests and optional `stopWhen`.

Transport

- [ ] If custom endpoint or headers are required, use `transport` options or `headers` in `useChat` calls.

Docs

- [x] ADR-0015 documents the design and rationale.

Validation

- [ ] Manual test: send a prompt, observe streaming parts; tool calls produce `tool-*` parts.
