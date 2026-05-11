# ADR-0066: AI SDK v6 agents, MCP, and message persistence

**Version**: 1.1.0
**Status**: Accepted
**Date**: 2026-01-05
**Category**: AI + fullstack
**Domain**: AI SDK, agent workflows, tools, persistence

## Context

TripSage is agentic:

- Tool use (search, calendar, memory, itinerary operations)
- Streaming responses
- Tool approval UX
- Persistence for auditability and resumable sessions

AI SDK v6 provides first-class streaming and tool primitives, plus MCP support.

## Decision

- Use AI SDK v6:
  - `streamText` as the primary streaming primitive
  - tools defined server-side with Zod schemas
  - a controlled agent loop (manual loop where needed) for deterministic behavior
- Message persistence:
  - Store chat sessions and messages in Supabase with RLS.
  - Persist only non-tool UI message parts in `chat_messages.content`.
  - Persist tool invocations and tool results in `chat_tool_calls`; this table is
    the authoritative lifecycle store for tool state.
  - Rehydrate persisted tool rows as AI SDK v6 static tool UI parts with
    `tool-${toolName}` part types. Do not keep legacy `tool-call`,
    `tool-result`, `dynamic-tool`, or approval tool parts in stored message
    content.
- MCP:
  - Enable MCP clients on the server where it provides value (tool registry, external knowledge sources).
  - Keep MCP credentials server-only.

## Consequences

- Clean, provider-agnostic AI integration.
- Strong audit and replay capability.
- Requires careful schema design for tool inputs/outputs and message formats.
- Stored chat content remains stable across AI SDK UI part changes because tool
  state is canonicalized out of `chat_messages.content`.
- Existing persisted tool-shaped content is canonicalized by migration
  `20260511020000_canonicalize_chat_message_parts.sql`.
- Existing seed agent configs using old GPT-4o-era defaults are moved to the
  current repo default by `20260511021000_refresh_agent_config_model_defaults.sql`
  without touching admin-created/custom model identifiers.

## References

```text
AI SDK docs: https://ai-sdk.dev/docs
AI SDK 6 migration guide: https://ai-sdk.dev/docs/migration-guides/migration-guide-6-0
Chatbot tool usage: https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-tool-usage
Manual agent loop cookbook: https://ai-sdk.dev/cookbook/node/manual-agent-loop
Vercel MCP docs: https://vercel.com/docs/mcp
AI SDK GitHub: https://github.com/vercel/ai
```
