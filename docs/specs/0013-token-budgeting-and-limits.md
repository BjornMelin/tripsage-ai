# Spec: Token Budgeting & Limits

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-01
**Category**: frontend
**Domain**: AI SDK / Next.js App Router
**Related ADRs**: [ADR-0027](adr-0027-token-budgeting-and-limits.md)
**Related Specs**: [SPEC-0008](spec-ai-sdk-v6-foundations.md)

## Interfaces

```bash
// frontend/src/lib/tokens/limits.ts
export type ModelLimitsTable = Record<string, number>;
export const MODEL_LIMITS: ModelLimitsTable;
export const DEFAULT_CONTEXT_LIMIT: number;
export function getModelContextLimit(modelName?: string, table?: ModelLimitsTable): number;

// frontend/src/lib/tokens/budget.ts
export type ChatMessage = { role: 'system'|'user'|'assistant'; content: string };
export const CHARS_PER_TOKEN_HEURISTIC = 4;
export function countTokens(texts: string[], modelHint?: string): number;
export type ClampResult = { maxTokens: number; reasons: string[] };
export function clampMaxTokens(messages: ChatMessage[], desiredMax: number, modelName?: string, table?: Record<string, number>): ClampResult;
export function countPromptTokens(messages: ChatMessage[], modelHint?: string): number;
```

## Model Limits

- OpenAI: `gpt-4o` 128k, `gpt-4o-mini` 128k, `gpt-5` 200k, `gpt-5-mini` 200k.
- Anthropic: `claude-3.5-sonnet` 200k, `claude-3.5-haiku` 200k.
- xAI: conservative default 128k.
- Unknown models: default 128k.

## Counting

- Prefer provider usage when available.
- OpenAI: `js-tiktoken/lite` with `o200k_base` (modern) and `cl100k_base` (older) encodings.
- Others: heuristic ~4 chars/token (UNVERIFIED). Documented in code and tests.

## Clamping

- Inputs: messages (content-only for counting), desiredMax, modelName.
- Compute: `available = max(0, limit - promptTokens)` where `limit = getModelContextLimit(modelName)`.
- Result: `maxTokens = max(1, min(desiredMax, available))`.
- Reasons:
  - `maxTokens_clamped_model_limit` when desired exceeds available or available is 0.
  - `maxTokens_clamped_invalid_desired` when desired <= 0 (coerced to 1).

## Error Handling & Safeguards

- Unknown models → default limit; warn at call sites if needed.
- Tokenizer selection failures fall back to heuristic; no exceptions leak.

## Tests

- Unit tests for counting (empty, basic string, unknown model heuristic).
- Unit tests for clamping (exceeding limits, invalid desired, unknown model default).
