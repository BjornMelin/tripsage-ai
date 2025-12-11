# AI Integration (Vercel AI SDK v6)

Patterns and options for configuring providers via the Vercel AI Gateway and direct keys.

## Gateway `providerOptions`

Use `providerOptions.gateway` in `streamText`/`generateText` calls when the resolved model is a Gateway model (user or team scoped). Keep routing logic in route handlers, not in the registry.

### Round-robin across two providers

```ts
const result = await streamText({
  model,
  messages,
  providerOptions: {
    gateway: { order: ["openai", "anthropic"] },
  },
});
```

### Prefer Anthropic, then OpenAI, with budget guard

```ts
const result = await streamText({
  model,
  messages,
  providerOptions: {
    gateway: {
      order: ["anthropic", "openai"],
      budgetTokens: 200_000,
    },
  },
});
```

### Route thinking models to Anthropic only

```ts
const result = await streamText({
  model,
  messages,
  providerOptions: {
    gateway: {
      order: /think|reason/i.test(JSON.stringify(messages))
        ? ["anthropic"]
        : ["openai", "anthropic"],
    },
  },
});
```

## Best Practices

- Keep `providerOptions` close to route handlers (avoid encoding in the provider registry).
- Pair routing with per-request token budgets and chat limits.
- Prefer Gateway API keys (`AI_GATEWAY_API_KEY`) for multi-provider routing; fall back to BYOK keys when users supply them.
- Tests: use `MockLanguageModelV3` and assert `providerOptions` on recorded calls.

## Related Docs

- [AI Tools](ai-tools.md) - Tool creation with `createAiTool` factory and guardrails
- [Zod Schema Guide](zod-schema-guide.md) - Tool input schema patterns
- [Observability](observability.md) - Spans/events via `@/lib/telemetry/*` around AI calls
- `src/ai/models/registry.ts` (BYOK registry)
- `src/app/api/*` route handlers for per-request routing
