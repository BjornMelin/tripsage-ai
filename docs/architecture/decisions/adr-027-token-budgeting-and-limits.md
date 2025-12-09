# ADR: Token Budgeting & Limits (Counting + Clamping)

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-01
**Category**: frontend
**Domain**: AI SDK / Next.js App Router
**Related ADRs**: [ADR-0023](adr-0023-adopt-ai-sdk-v6-foundations.md)
**Related Specs**: [SPEC-0008](spec-ai-sdk-v6-foundations.md)

## Context

We are migrating to AI SDK v6 and must enforce safe token budgets across providers. Accurate token usage is reported by providers when available. For planning and guardrails, we need a robust fallback for counting tokens and clamping `maxOutputTokens` against context limits.

## Decision

1. Use provider-reported usage as the source of truth whenever available.
2. For OpenAI models, use `js-tiktoken` (lite) to estimate prompt token counts.
3. For non-OpenAI models (Anthropic, xAI) without a first-party JS tokenizer, use a conservative heuristic of ~4 characters per token (approximation; verify against provider usage where available).
4. Maintain a per-model context window table in TypeScript; default to 128k when unknown.
5. Clamp `maxOutputTokens` to `max(1, min(desiredMax, limit - promptTokens))`, recording reasons when clamped.

## Alternatives Considered

- Do nothing: risk exceeding context limits and inconsistent budgeting.
- Server-only estimation: increases coupling and duplicates logic between runtimes.
- Full SDK-specific tokenizers for each provider: higher complexity; low marginal value now.

## Consequences

- Simpler, low-maintenance client utilities with clear fallbacks.
- Deterministic clamping behavior and test coverage.
- Python-side estimation remains until the Python routes are fully decommissioned (tracked for later removal per migration plan).

## Implementation

- `src/lib/tokens/limits.ts`: model limit table and helper.
- `src/lib/tokens/budget.ts`: `countTokens`, `clampMaxTokens` utilities.
- AI route uses `clampMaxTokens` to set `maxOutputTokens`.
- Vitest covers counting and clamping edge cases.

## Security & Privacy

- No PII is logged. Utilities operate on provided strings only.
- Safe defaults prevent large, unexpected generations.

## Follow-ups

- Prefer provider usage metadata in all AI routes; expand when the SDK exposes streaming usage uniformly.
- Remove Python-side token estimation upon final migration of routes to TS utilities.
