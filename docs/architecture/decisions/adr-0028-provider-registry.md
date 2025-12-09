# ADR-0028: Provider Registry & Resolution

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-01
**Category**: frontend
**Domain**: AI SDK / Next.js App Router
**Related ADRs**: [ADR-0023](adr-0023-adopt-ai-sdk-v6-foundations.md)
**Related Specs**: [SPEC-0008](spec-ai-sdk-v6-foundations.md)

## Context

We are migrating to AI SDK v6 providers and removing Python-based provider wrappers. We need a single server-only registry that:

- Resolves a user's BYOK provider key via Supabase RPCs.
- Applies a strict preference order: openai → openrouter → anthropic → xai (configurable).
- Returns an AI SDK `LanguageModel` ready for downstream use.

## Decision

- Implement `src/ai/models/registry.ts` with `resolveProvider(userId, modelHint?)`.
- Use provider factories with BYOK:
  - OpenAI: `createOpenAI({ apiKey })`
  - OpenRouter: `createOpenAI({ apiKey, baseURL: 'https://openrouter.ai/api/v1' })`
  - Anthropic: `createAnthropic({ apiKey })`
  - xAI: `createXAI({ apiKey })` from `@ai-sdk/xai`
  - Per-user Gateway BYOK: `createGateway({ apiKey, baseURL? })` from `ai` (v6)
- Server-only: `server-only` import guard. No secrets are ever returned to the client.
- Remove Python provider wrappers and tests.

## Consequences

- Downstream routes consume a single `LanguageModel` interface. No back-compat shims.
- Per-user Gateway is supported as a first-class BYOK provider.

## Alternatives Considered

- Using the community `@openrouter/ai-sdk-provider`: rejected for v6 because the OpenAI-compatible provider with `baseURL` is simpler, first‑party, and avoids an extra dependency while matching OpenRouter’s OpenAI API compatibility.

## Security

- BYOK fetched with SECURITY DEFINER RPCs; keys exist only in server memory of route handlers and registry. No client exposure.

## Gateway Compatibility

- If Vercel AI Gateway is enabled, the registry can still fall back to Gateway keys. No attribution logic is required. In v6, `createGateway` is exported from the `ai` package, and both user and team Gateway paths use `createGateway` for parity.

## Testing Status

- Vitest unit tests cover provider precedence and OpenRouter resolution without attribution headers in `src/lib/providers/__tests__/registry.test.ts`.
- Chat streaming adds `provider` to message metadata for observability and debugging.
