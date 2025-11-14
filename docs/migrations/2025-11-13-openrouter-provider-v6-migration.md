# Title: Switch OpenRouter to OpenAI-compatible provider (AI SDK v6)

**Date**: 2025-11-13

**Summary**: Switch OpenRouter to OpenAI-compatible provider (AI SDK v6)

## Summary

- Replace `@openrouter/ai-sdk-provider` with first-party `@ai-sdk/openai` configured with `baseURL: https://openrouter.ai/api/v1`.
- Keep attribution headers removed (no `HTTP-Referer`, no `X-Title`).
- Aligns with AI SDK v6 guidance and reduces dependencies.

## What changed

- Registry: `frontend/src/lib/providers/registry.ts` now uses `createOpenAI({ apiKey, baseURL: 'https://openrouter.ai/api/v1' })` for OpenRouter BYOK and server fallback.
- Validate route: `frontend/src/app/api/keys/validate/route.ts` builds OpenRouter checks using `createOpenAI` with `baseURL`.
- Tests: Updated OpenRouter expectations to reflect OpenAI-compatible provider and removed OpenRouter provider mocks.
- Package: Remove `@openrouter/ai-sdk-provider` from `frontend/package.json`.
- Docs: Updated ADR-0028 and SPEC-0012; AGENTS.md reflects the new mapping.

## Why

- AI SDK v6 exposes Gateway in `ai` and first-party providers for OpenAI/Anthropic/xAI. OpenRouter is OpenAI-compatible and works with `createOpenAI` + `baseURL`, simplifying integration.
- The community provider adds an extra dependency without compelling benefits for our usage.

## How to verify

1) `cd frontend && pnpm install`
2) `pnpm biome:check && pnpm type-check`
3) `pnpm test:run`
4) Manual smoke: POST `{ service: 'openrouter', apiKey: '...' }` to `/api/keys/validate` and expect `{ isValid: true }` with a valid key.

## Notes

- This migration supersedes the earlier doc "2025-11-13-openrouter-official-provider.md".
