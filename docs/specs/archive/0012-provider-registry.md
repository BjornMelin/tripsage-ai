# SPEC-0012: Provider Registry

**Version**: 1.0.0
**Status**: Accepted (archived; current runtime details are documented in `docs/development/ai/ai-integration.md` and `docs/architecture/database.md`)
**Date**: 2025-11-01
**Category**: frontend
**Domain**: AI SDK / Next.js App Router
**Related ADRs**: [ADR-0028](../../architecture/decisions/adr-0028-provider-registry.md)
**Related Specs**: [SPEC-0008](0008-spec-ai-sdk-v6-foundations.md)

## API

```bash
function resolveProvider(userId: string, modelHint?: string): Promise<ProviderResolution>
```

### Types

- `ProviderId` = `"openai" | "openrouter" | "anthropic" | "xai"`
- `ProviderResolution` = `{ provider: ProviderId; credentialSource: "user-gateway" | "user-provider" | "team-gateway" | "server-provider"; modelId: string; model: LanguageModel; maxOutputTokens?: number }`

Behavior:

- Provider resolution order is owned by `docs/operations/runbooks/byok-gateway-operator.md`.
- Consent: if user setting `allowGatewayFallback` is false and no BYOK keys are present, resolution throws instead of using team Gateway.

## Integration Mapping

- OpenAI → `createOpenAI({ apiKey }).responses(modelId)`; default model mapping: `gpt-5.4-mini`.
- OpenRouter → `createOpenAI({ apiKey, baseURL: 'https://openrouter.ai/api/v1' })(modelId)` (OpenAI‑compatible endpoint).
- Anthropic → `createAnthropic({ apiKey })(modelId)`; no implicit app-owned default.
- xAI → `createXAI({ apiKey })(modelId)` from `@ai-sdk/xai`; default model mapping: `grok-4.3`.
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

Env sources: none (no attribution headers required). User setting: `allowGatewayFallback` (default false).

## Tests

- Validate the provider-resolution order owned by `docs/operations/runbooks/byok-gateway-operator.md`.
- Validate provider-specific model mapping, including OpenRouter's OpenAI-compatible endpoint.
- Use Anthropic only when an explicit current model is selected.
- Throw when no keys exist.
- Ensure no secrets are present in returned object.

## User Settings API (consent)

- Route: `GET /api/user-settings` → `{ allowGatewayFallback: boolean | null }`
- Route: `POST /api/user-settings` with `{ allowGatewayFallback: boolean }` to upsert per-user consent (RLS owner-write). Uses SSR Supabase client; no secrets returned.

## ProviderOptions with Gateway (examples)

When using a Gateway model (either user or team), callers can pass supported `providerOptions.gateway` values to influence routing at the request level:

```ts
import { streamText } from "ai";

const result = await streamText({
  model: gatewayModel, // from resolveProvider(...)
  messages,
  providerOptions: {
	    gateway: {
	      order: ["anthropic", "openai"],
	      tags: ["tripsage:chat"],
	      zeroDataRetention: true,
	    },
	  },
});
```

Notes:

- Keep `providerOptions` usage close to route handlers; the registry intentionally does not bake these policies in.
- See README for end-to-end snippets and cautions.
