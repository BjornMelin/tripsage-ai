# Spec: AI Elements Chat UI

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-01
**Category**: frontend
**Domain**: AI SDK / Next.js App Router
**Related ADRs**: [ADR-0026](adr-0026-adopt-ai-elements-ui-chat.md)
**Related Specs**: [SPEC-0008](spec-ai-sdk-v6-foundations.md)

## Overview

Provide a simple, accessible chat UI composed of AI Elements primitives and powered by AI SDK v6 streaming via a Next.js route.

## Components

- Conversation primitives (`Conversation`, `ConversationContent`, `ConversationEmptyState`, `ConversationScrollButton`).
- Message primitives (`Message`, `MessageAvatar`, `MessageContent`).
- Prompt input primitives (`PromptInput`, header/body/footer regions, attachments list, submit button, action menu).

## API Contract

- Client: `useChat` from `@ai-sdk/react` with `DefaultChatTransport`.
- Server: `POST /api/chat/stream` accepts `{ messages: UIMessage[] }`.
- Server response: DataStream (SSE) via `toDataStreamResponse()`.

## Tool Usage (MVP)

- Demo tools (`weather`, `convertFahrenheitToCelsius`) enabled in route to exercise tool rendering paths.
- Message renderer displays tool parts as structured JSON blocks.

## Accessibility

- Conversation region uses `role="log"`.
- Submit button has `aria-label`.
- Prompt textarea has accessible label.

## Testing

- Vitest + RTL: render chat page; simulate prompt submission; mock SSE response and assert assistant text appears.
