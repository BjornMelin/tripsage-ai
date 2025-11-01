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
- `ProviderResolution` = `{ provider: ProviderId; modelId: string; model: LanguageModel; headers?: Record<string,string>; maxTokens?: number }`

Behavior:

- Iterate preference order from `getProviderSettings().preference`.
- For each provider, call `getUserApiKey(userId, provider)`.
- On first key found:
  - Build model via provider factory (see Integration Mapping below).
  - Attach headers only for OpenRouter (attribution).
  - Return `ProviderResolution`.
- If no keys found: throw `Error("No provider key found for user…")`.

## Integration Mapping

- OpenAI → `createOpenAI({ apiKey })(modelId)`; default model mapping: `gpt-4o-mini`.
- OpenRouter → `createOpenAI({ apiKey, baseURL: 'https://openrouter.ai/api/v1', headers })(modelId)`; headers from env `OPENROUTER_REFERER`, `OPENROUTER_TITLE`.
- Anthropic → `createAnthropic({ apiKey })(modelId)`; default model mapping: `claude-3-5-sonnet-20241022`.
- xAI → `createOpenAI({ apiKey, baseURL: 'https://api.x.ai/v1' })(modelId)`; default model mapping: `grok-3`.

## Model Hint Mapping

- If `modelHint` is falsy, use defaults per provider above.
- For OpenRouter, accept fully qualified ids (`provider/model`) without transformation.
- Otherwise, return hint as-is.

## Settings

`getProviderSettings()` returns:

```ts
interface ProviderSettings {
  preference: ProviderId[];
  openrouterAttribution?: { referer?: string; title?: string };
}
```

Env sources:

- `OPENROUTER_REFERER` → `openrouterAttribution.referer`
- `OPENROUTER_TITLE` → `openrouterAttribution.title`

## Tests

- Prefer OpenAI when `openai` key exists.
- Fallback to OpenRouter and attach attribution headers.
- Fallback to Anthropic/xAI.
- Throw when no keys exist.
- Ensure no secrets are present in returned object.
