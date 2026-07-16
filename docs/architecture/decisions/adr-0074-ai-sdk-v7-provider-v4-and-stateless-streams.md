# ADR-0074: Adopt AI SDK v7 Provider V4 and stateless streams

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2026-07-15
**Category**: AI + fullstack
**Domain**: AI SDK, providers, agents, streaming, telemetry
**Related ADRs**: ADR-0023, ADR-0024, ADR-0028, ADR-0031, ADR-0033, ADR-0044, ADR-0046, ADR-0051, ADR-0066
**Related Specs**: SPEC-0103, SPEC-0104

## Context

AI SDK v7 requires Node.js 22 or newer, publishes ECMAScript modules (ESM) only, and uses the Provider V4 model contract. It also replaces several v6 compatibility surfaces with stable names and composable stream helpers. Keeping v6 aliases would preserve two ways to express the same runtime behavior and delay failures until a later major upgrade.

TripSage already runs Node.js 24 and uses request-scoped Next.js route handlers. A direct hard cut keeps provider selection, streaming, telemetry, and message persistence on one supported contract.

## Decision

- Use AI SDK v7 and Provider V4 packages only. Run AI code on Node.js 22 or newer and import AI SDK packages through ESM syntax.
- Return Provider V4 models directly from the server-only registry:
  - OpenAI uses `.responses()`
  - OpenRouter uses the OpenAI-compatible `.chat()` surface
  - Anthropic uses `.languageModel()`
  - xAI uses `.chat()` explicitly to preserve the existing chat-completions behavior
  - Vercel AI Gateway returns its Provider V4 model without a local coercion adapter
- Use `instructions` for trusted server instructions. Do not place user-controlled system messages in `messages`.
- Keep agent instructions static and server-owned. Encode validated request parameters only in the canonical user message; never interpolate request values into privileged instructions.
- Hard-cut client-authored `system` roles from `/api/ai/stream`; the endpoint accepts only `user` and `assistant` messages.
- Reconstruct submitted user messages from approved text/file fields before persistence or provider conversion. Client provider references, provider metadata/options, reasoning, source, data, and tool parts are never trusted.
- Keep retrieved memory out of privileged instructions. Encode bounded memory as a user-role `memoryContext` JSON message immediately before the latest user request, with a static instruction declaring that field untrusted reference data.
- Apply `20260716000000_correct_legacy_tool_execution_ownership.sql` before the v7 application release so terminal v6 app-tool rows resume as locally executed calls rather than provider-native item references.
- Use stable v7 Core and agent callbacks and options: `repairToolCall`, `onEnd`, and `onStepEnd`. Do not add v6 aliases. The `useChat` hook retains its native `onFinish` callback.
- Keep streams stateless. Core `streamText` routes convert `result.stream` with
  top-level `toUIMessageStream()`, then return it with
  `createUIMessageStreamResponse()`. `ToolLoopAgent` routes use the native
  `createAgentUIStreamResponse()` helper. Route handlers own authentication,
  persistence, and error handling.
- Register `@ai-sdk/otel` once after `@vercel/otel`. Put low-cardinality call context in `runtimeContext` and include only explicit keys through `telemetry.includeRuntimeContext`. Never record prompts, outputs, headers, secrets, raw user identifiers, or request identifiers.
- Preserve persisted `reasoning-file` parts only when `mediaType` and `url` pass validation. Accept `http`, `https`, or matching valid base64 data URLs. Render through the existing safe attachment path, never render data URLs directly, and budget only `[reasoning-file:<mediaType>]` instead of URL data.
- Keep the product boundaries from ADR-0031, ADR-0033, ADR-0044, ADR-0051,
  and ADR-0066. This ADR supersedes the AI SDK v6 runtime, API-name, provider,
  streaming, and environment-variable surfaces in ADR-0023, ADR-0031,
  ADR-0033, ADR-0044, ADR-0051, and ADR-0066.
- Track live provider and deployment verification in [issue #766](https://github.com/BjornMelin/tripsage-ai/issues/766). Missing operator-managed secrets do not authorize code fallbacks, embedded credentials, or skipped production checks.

## Consequences

### Positive

- The runtime uses one current API surface without deprecated compatibility paths.
- Provider selection preserves each provider's intended transport.
- Core and `ToolLoopAgent` routes use native v7 stream helpers without result-instance compatibility methods.
- Telemetry follows the AI SDK's native OpenTelemetry integration with an explicit data boundary.
- Reasoning files remain resumable without exposing untrusted inline data.

### Negative

- Node.js 18, Node.js 20, and CommonJS consumers are unsupported.
- New AI SDK upgrades must preserve Provider V4 and reasoning-file exhaustiveness.
- Live provider verification remains blocked until an operator completes issue #766.

### Neutral

- Supabase row-level security, message persistence, tool lifecycle storage, and provider resolution order remain unchanged.

## Alternatives considered

### Keep v6 aliases during a transition

Rejected. The repository ships as one Next.js application, so dual callback, prompt, and stream contracts add maintenance without enabling an independent rollout.

### Add local provider adapters

Rejected. Official Provider V4 factories already return compatible models and preserve provider-specific transports.

## References

- [ADR-0023: Adopt AI SDK v6 foundations](adr-0023-adopt-ai-sdk-v6-foundations.md)
- [ADR-0024: BYOK routes and security](adr-0024-byok-routes-and-security.md)
- [ADR-0028: Provider registry](adr-0028-provider-registry.md)
- [ADR-0031: Next.js chat API and AI SDK v6](adr-0031-nextjs-chat-api-ai-sdk-v6.md)
- [ADR-0033: RAG advanced v6](adr-0033-rag-advanced-v6.md)
- [ADR-0044: Tool registry](adr-0044-tool-registry-ts.md)
- [ADR-0046: OpenTelemetry tracing](adr-0046-otel-tracing-frontend.md)
- [ADR-0051: Agent router workflows](adr-0051-agent-router-workflows.md)
- [ADR-0066: AI SDK v6 agents, MCP, and message persistence](adr-0066-ai-sdk-v6-agents-mcp-and-message-persistence.md)
- [AI SDK 7 migration guide](https://ai-sdk.dev/docs/migration-guides/migration-guide-7-0)
- [AI SDK telemetry](https://ai-sdk.dev/docs/ai-sdk-core/telemetry)
- [AI SDK streamText reference](https://ai-sdk.dev/docs/reference/ai-sdk-core/stream-text)
- [AI SDK ToolLoopAgent reference](https://ai-sdk.dev/docs/reference/ai-sdk-core/tool-loop-agent)
- [TripSage live environment follow-up](https://github.com/BjornMelin/tripsage-ai/issues/766)
