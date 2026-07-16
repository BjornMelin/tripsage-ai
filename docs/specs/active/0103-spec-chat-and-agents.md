# SPEC-0103: Chat and agents (AI SDK v7)

**Version**: 2.0.0
**Status**: Final  
**Date**: 2026-07-15

## Goals

- Streaming chat with tool usage.
- Agent tools are typed, validated, auditable, and safe.
- Chat sessions persist and can be resumed.

## Chat model

- chat
  - id, user_id, trip_id nullable, title, created_at
- chat_message
  - chat_id, role, parts JSONB, metadata JSONB, created_at
- chat_tool_calls
  - message_id, tool_call_id, tool_name, state, input_json, output_json, error_json, created_at

## Tooling

Required tools (initial set):

- trips.getTrip(tripId)
- trips.updateTripPreferences(tripId, patch)
- searchPlaces(query, near, filters)
- memory.search(query, namespace)
- attachmentsList(chatId)
- rag.search(query, tripId, chatId)

Tool constraints:

- All tool inputs are Zod-validated.
- Tools enforce authorization via userId and RLS.
- Tool execution approval is supported in UI where needed.
- Agents use Provider V4 models and stable AI SDK v7 Core settings: `instructions`, `repairToolCall`, `onEnd`, and `onStepEnd`. Agent instructions are static and server-owned; validated request parameters remain in user messages. The `useChat` hook keeps its native `onFinish` callback.
- xAI BYOK resolution uses `.chat()` explicitly; OpenAI uses `.responses()`, OpenRouter uses `.chat()`, and Anthropic uses `.languageModel()`.

## Endpoint strategy

- Streaming Route Handler:
  - POST /api/chat
  - Uses AI SDK v7 `streamText`, converts `result.stream` with `toUIMessageStream()`, and returns `createUIMessageStreamResponse()`
  - Passes `originalMessages` to the stateless converter to avoid duplicate assistant messages
  - `convertToModelMessages()` is awaited when transforming UI messages to model messages
- Server Actions for non-stream mutations (rename chat, delete chat)

## Persistence and reasoning files

- Persist non-tool UI message parts in `chat_messages.content`; keep tool lifecycle state in `chat_tool_calls`.
- Keep a `reasoning-file` part only when its media type and URL pass validation.
- Accept `http`, `https`, or a valid base64 data URL whose declared media type matches the part.
- Render reasoning files through the safe attachment path. Never render a data URL directly.
- Token budgeting counts `[reasoning-file:<mediaType>]`, not the file URL or base64 body.

## UI flows

- Chat page:
  - left sidebar: chats and trips
  - main: conversation stream + tool UI blocks
  - right panel: “Sources” (places, itinerary changes)

## References

- AI SDK docs: <https://ai-sdk.dev/docs>
- Chatbot tool usage: <https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-tool-usage>
- Manual agent loop: <https://ai-sdk.dev/cookbook/node/manual-agent-loop>
