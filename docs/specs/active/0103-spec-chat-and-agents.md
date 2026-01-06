# SPEC-0103: Chat and agents (AI SDK v6)

**Version**: 1.0.0  
**Status**: Final  
**Date**: 2026-01-05

## Goals

- Streaming chat with tool usage.
- Agent tools are typed, validated, auditable, and safe.
- Chat sessions persist and can be resumed.

## Chat model

- chat
  - id, user_id, trip_id nullable, title, created_at
- chat_message
  - chat_id, role, content, created_at
  - tool_invocations JSONB (optional)
  - tool_results JSONB (optional)

## Tooling

Required tools (initial set):

- trips.getTrip(tripId)
- trips.updateTripPreferences(tripId, patch)
- search.places(query, near, filters)
- memory.search(query, namespace)
- attachments.list(chatId)
- rag.search(query, tripId, chatId)

Tool constraints:

- All tool inputs are Zod-validated.
- Tools enforce authorization via userId and RLS.
- Tool execution approval is supported in UI where needed.

## Endpoint strategy

- Streaming Route Handler:
  - POST /api/chat
  - Uses AI SDK v6 `streamText`
- Server Actions for non-stream mutations (rename chat, delete chat)

## UI flows

- Chat page:
  - left sidebar: chats and trips
  - main: conversation stream + tool UI blocks
  - right panel: “Sources” (places, itinerary changes)

## References

```text
AI SDK docs: https://ai-sdk.dev/docs
Chatbot tool usage: https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-tool-usage
Manual agent loop: https://ai-sdk.dev/cookbook/node/manual-agent-loop
```
