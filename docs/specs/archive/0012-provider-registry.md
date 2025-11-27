# Spec: Provider Registry

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-01
**Category**: frontend
**Domain**: AI SDK / Next.js App Router
**Related ADRs**: [ADR-0028](adr-0028-provider-registry.md)
**Related Specs**: [SPEC-0008](spec-ai-sdk-v6-foundations.md)

## API

```bash
function resolveProvider(userId: string, modelHint?: string): Promise<ProviderResolution>
```

### Types

- `ProviderId` = `"openai" | "openrouter" | "anthropic" | "xai"`
- `ProviderResolution` = `{ provider: ProviderId; modelId: string; model: LanguageModel; maxTokens?: number }`

Behavior:

- Resolution order per user:
  1) Per-user Gateway key (service `gateway`) → `@ai-sdk/gateway` with user API key and optional base URL; use model strings (e.g., `anthropic/claude-sonnet-4`).
  2) Per-provider BYOK (OpenAI/OpenRouter/Anthropic/xAI) → official providers; first found by preference order.
  3) Team Gateway fallback (if configured) → `AI_GATEWAY_API_KEY`/`AI_GATEWAY_URL`.
- Consent: if user setting `allowGatewayFallback` is false and no BYOK keys are present, resolution throws instead of using team Gateway.

## Integration Mapping

- OpenAI → `createOpenAI({ apiKey })(modelId)`; default model mapping: `gpt-4o-mini`.
- OpenRouter → `createOpenAI({ apiKey, baseURL: 'https://openrouter.ai/api/v1' })(modelId)` (OpenAI‑compatible endpoint).
- Anthropic → `createAnthropic({ apiKey })(modelId)`; default model mapping: `claude-3-5-sonnet-20241022`.
- xAI → `createXAI({ apiKey })(modelId)` from `@ai-sdk/xai`; default model mapping: `grok-3`.
- Gateway (user/team) → `createGateway({ apiKey, baseURL? })(modelId)` from `ai` (AI SDK v6 exports Gateway in the core package). Team fallback path now uses createGateway for parity with user BYOK Gateway.

## Model Hint Mapping

- If `modelHint` is falsy, use defaults per provider above.
- For OpenRouter, accept fully qualified ids (`provider/model`) without transformation.
- Otherwise, return hint as-is.

## Settings

`getProviderSettings()` returns:

```ts
interface ProviderSettings { preference: ProviderId[] }
```

Env sources: none (no attribution headers required). User setting: `allowGatewayFallback` (default true).

## Tests

- Prefer OpenAI when `openai` key exists.
- Fallback to OpenRouter.
- Fallback to Anthropic/xAI.
- Throw when no keys exist.
- Ensure no secrets are present in returned object.

## User Settings API (consent)

- Route: `GET /api/user-settings` → `{ allowGatewayFallback: boolean | null }`
- Route: `POST /api/user-settings` with `{ allowGatewayFallback: boolean }` to upsert per-user consent (RLS owner-write). Uses SSR Supabase client; no secrets returned.

## ProviderOptions with Gateway (examples)

When using a Gateway model (either user or team), callers can pass `providerOptions` to influence routing/budgeting at the request level:

```ts
import { streamText } from "ai";

const result = await streamText({
  model: gatewayModel, // from resolveProvider(...)
  messages,
  providerOptions: {
    gateway: {
      order: ["anthropic", "openai"],
      // optional budgeting knobs (example names; consult Gateway docs)
      budgetTokens: 200_000,
    },
  },
});
```

Notes:

- Keep `providerOptions` usage close to route handlers; the registry intentionally does not bake these policies in.
- See README for end-to-end snippets and cautions.
