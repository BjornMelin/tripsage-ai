# AI Observability (OpenTelemetry)

This document covers AI-specific observability patterns (spans, events, and structured logs) for TripSage.

For the canonical repo-wide standards (server + client), see:

- [Observability](../backend/observability.md#approved-telemetry--logging-entrypoints)

## Principles

- Prefer the repo helpers over direct OpenTelemetry API usage:
  - `withTelemetrySpan()` / `withTelemetrySpanSync()` from `src/lib/telemetry/span.ts`
  - `createServerLogger()` from `src/lib/telemetry/logger.ts`
  - `recordTelemetryEvent()` for lightweight events
- Keep attributes **low-cardinality** and **PII-safe** (no emails, raw user IDs, raw message content).

## AI SDK v7 telemetry

`src/instrumentation.ts` registers `@ai-sdk/otel` after `@vercel/otel`. AI SDK calls use `telemetry` with a stable `functionId`:

- Use consistent `functionId` values for routing, tools, and agent workflows.
- Put low-cardinality values in `runtimeContext` and opt in each emitted key through `telemetry.includeRuntimeContext`.
- Never include prompts, outputs, headers, secrets, raw identifiers, request IDs, model hints, or namespaces.
- Keep `recordInputs: false` and `recordOutputs: false` on every AI SDK call,
  including core generation, embedding, and `ToolLoopAgent` operations.

The current `functionId` catalog lives in [Observability](../backend/observability.md#ai-sdk-telemetry).

## Tool telemetry (`createAiTool`)

AI tools should be defined via `createAiTool` so they inherit common guardrails:

- telemetry spans/events
- cache and rate-limit attribution
- error normalization/redaction

Prefer adding tool-specific span attributes via the `telemetry.attributes` builder (counts, flags, provider names), not raw request payloads.
