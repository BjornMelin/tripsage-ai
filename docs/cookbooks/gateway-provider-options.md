---
date: 2025-11-13
status: current
---

# Gateway ProviderOptions Cookbook (**AI SDK v6**)

This cookbook shows common `providerOptions.gateway` configurations you can apply in
`streamText`/`generateText` calls when the resolved model is a **Gateway model** (user or team).

## Round-robin Across Two Providers

```ts
const result = await streamText({
  model,
  messages,
  providerOptions: {
    gateway: { order: ["openai", "anthropic"] },
  },
});
```

## Prefer Anthropic, Then OpenAI, with Budget Guard

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

## Route Thinking Models to Anthropic Only

```ts
const messages = [ /* ... */ ];
const result = await streamText({
  model,
  messages,
  providerOptions: {
    gateway: {
      // a model-hint based router (applied by your route handler)
      order: messages.some(m => /think|reason/i.test(JSON.stringify(m)))
        ? ["anthropic"]
        : ["openai", "anthropic"],
    },
  },
});
```

## Notes

### Best Practices

- Keep `providerOptions` close to route handlers (**do not encode in registry**)
- Combine with **per-request token budgets** and your chat limits

### Additional Resources

- See the **operator runbook** for consent model and fallback behaviors
