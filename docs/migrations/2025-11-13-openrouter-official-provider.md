# Title: (Superseded) Migrate to official OpenRouter provider and remove attribution headers

**Date**: 2025-11-13

**Summary**: (Superseded by 2025-11-13-openrouter-provider-v6-migration.md)

- Replaced OpenRouter integration using `createOpenAI({ baseURL: 'https://openrouter.ai/api/v1' })` with the official `@openrouter/ai-sdk-provider`.
- Removed all attribution headers (`HTTP-Referer`, `X-Title`) and related settings/tests.
- Updated docs, specs, and ADRs to reflect the official provider usage.

## What changed

- Registry: `frontend/src/lib/providers/registry.ts` now imports and uses `createOpenRouter({ apiKey })` for BYOK and server fallback.
- Settings: `frontend/src/lib/settings.ts` no longer derives or exposes `openrouterAttribution`.
- Types: `ProviderSettings` only has `preference: ProviderId[]`; `ProviderResolution.headers` removed.
- Keys validate route: `frontend/src/app/api/keys/validate/route.ts` uses `createOpenRouter` builder; no attribution headers.
- Tests: Updated and simplified to remove attribution assertions; added OpenRouter provider mock.
- Docs: Updated spec, ADR, README, and AGENTS entries; removed obsolete prompt doc.

## Why

- The official provider simplifies configuration, avoids manual baseURL/header wiring, and reduces maintenance.
- Attribution headers are optional for leaderboard tracking and not needed by this app.

## How to verify

1) Lint/format: `cd frontend && pnpm biome:check`
2) Types: `pnpm type-check`
3) Tests (targeted):
   - `pnpm vitest run src/lib/providers/__tests__/registry.test.ts`
   - `pnpm vitest run src/lib/__tests__/settings.test.ts`
   - `pnpm vitest run src/app/api/keys/validate/__tests__/route.test.ts`
4) Manual check (optional): set `OPENROUTER_API_KEY` and POST `{ service: 'openrouter', apiKey: '...' }` to `/api/keys/validate`.

## Notes

- Default OpenRouter model mapping is `openai/gpt-4o-mini` when `modelHint` is omitted.
- Gateway fallback remains unchanged.
