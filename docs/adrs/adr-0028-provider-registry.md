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
- Adds OpenRouter attribution headers (`HTTP-Referer`, `X-Title`).

## Decision

- Implement `frontend/src/lib/providers/registry.ts` with `resolveProvider(userId, modelHint?)`.
- Use provider factories with BYOK:
  - OpenAI: `createOpenAI({ apiKey })`
  - OpenRouter: `createOpenAI({ apiKey, baseURL: 'https://openrouter.ai/api/v1', headers })`
  - Anthropic: `createAnthropic({ apiKey })`
  - xAI: `createOpenAI({ apiKey, baseURL: 'https://api.x.ai/v1' })`
- Server-only: `server-only` import guard. No secrets are ever returned to the client.
- Remove Python provider wrappers and tests.

## Consequences

- All legacy Python provider code and tests are deleted. New TS tests cover resolution logic and attribution headers.
- Downstream routes consume a single `LanguageModel` interface. No back-compat shims.
- Attribution is centralized and testable.

## Alternatives Considered

- Community OpenRouter provider: rejected to reduce dependency surface and avoid peer conflicts; OpenAI-compatible client covers our needs while supporting headers.

## Security

- BYOK fetched with SECURITY DEFINER RPCs; keys exist only in server memory of route handlers and registry. No client exposure.
