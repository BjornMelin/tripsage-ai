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

## AI SDK v6 telemetry

AI SDK calls should use `experimental_telemetry` with a stable `functionId`:

- Use consistent `functionId` values for routing, tools, and agent workflows.
- Put only low-cardinality values in `metadata` (counts, booleans, enum-like strings).

The current `functionId` catalog lives in [Observability](../backend/observability.md#ai-sdk-telemetry-experimental_telemetry).

## Tool telemetry (`createAiTool`)

AI tools should be defined via `createAiTool` so they inherit common guardrails:

- telemetry spans/events
- cache and rate-limit attribution
- error normalization/redaction

Prefer adding tool-specific span attributes via the `telemetry.attributes` builder (counts, flags, provider names), not raw request payloads.
