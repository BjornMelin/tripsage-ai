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
- Use AI SDK timeout configuration (`timeout: { totalMs, stepMs }`) to cap total and per-step
  latency for streaming and tool loops.
- Prefer Gateway API keys (`AI_GATEWAY_API_KEY`) for multi-provider routing; fall back to BYOK keys when users supply them.
- Tests: use `MockLanguageModelV3` and assert `providerOptions` on recorded calls.

## AI SDK v6 Canonical Patterns

### Server route handler (streaming)

```ts
import { convertToModelMessages, streamText } from "ai";
import type { UIMessage } from "ai";

export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json();
  const result = streamText({
    model,
    messages: await convertToModelMessages(messages),
    tools,
  });

  return result.toUIMessageStreamResponse({
    originalMessages: messages,
    includeUsage: true,
    onError: (error) => (error instanceof Error ? error.message : "unknown_error"),
    messageMetadata: ({ part }) => {
      if (part.type === "start") return { sessionId: "server-session-id" };
      if (part.type === "finish") return { tokens: part.totalUsage?.totalTokens ?? 0 };
      return undefined;
    },
  });
}
```

### Client hook (useChat)

- Use `DefaultChatTransport` for static headers/body/credentials.
- Use `sendMessage(..., { headers, body, metadata })` for per-request overrides.
- Avoid hook-level `headers` or `body` in `useChat` options (deprecated in AI SDK v6).

```tsx
"use client";

import { DefaultChatTransport } from "ai";
import { useChat } from "@ai-sdk/react";

const { messages, sendMessage } = useChat({
  transport: new DefaultChatTransport({
    api: "/api/chat",
    headers: () => ({ Authorization: `Bearer ${token}` }),
  }),
});
```

### Common pitfalls

- **Duplicate assistant messages**: pass `originalMessages` to
  `toUIMessageStreamResponse()` when streaming.
- **Provider options**: `UIMessage` does not carry provider options. Use
  `convertToModelMessages()` with call options or inject options in the route handler.

## Timeouts

AI SDK v6 supports per-call timeouts with optional per-step limits. Prefer `timeout`
over manual `AbortController` timeouts so the SDK can surface structured aborts and
step-level cancellation.

```ts
const result = await streamText({
  model,
  messages,
  timeout: {
    totalMs: 30_000,
    stepMs: 15_000,
  },
});
```

Notes:

- Chat defaults use `CHAT_DEFAULT_TIMEOUT_SECONDS` (falls back to `maxDuration - 5`).
- Agent routes honor `config.parameters.timeoutSeconds` from agent configuration.

## UI Message Metadata & Data Parts

Use AI SDK v6 UI message metadata and data parts to expose model usage, finish
reason, and transient status updates to the client.

- Schemas live in `src/domain/schemas/ai.ts` (`chatMessageMetadataSchema`,
  `agentMessageMetadataSchema`, `chatDataPartSchemas`).
- Client: pass `messageMetadataSchema` + `dataPartSchemas` to `useChat`.
- Server: attach metadata via `messageMetadata` in `toUIMessageStream`, and
  stream transient data parts via `createUIMessageStream` + `writer.write`.
- Enable `sendSources: true` to include `source-url` parts for citations.

## Provider Metadata During Tool Input Streaming

Starting with `ai` v6.0.39+, provider-executed tools (e.g. MCP tools) can attach
provider metadata while the tool call is still in `state: "input-streaming"`
(via `callProviderMetadata` on tool parts).

Guidelines:

- Do not strip unknown keys from tool parts in the UI. Tool parts may include
  `callProviderMetadata` even before inputs are fully available.
- Prefer rendering metadata in a safe, redacted way (tokens/keys removed) when
  surfaced to users.

## Related Docs

- [AI Tools](ai-tools.md) - Tool creation with `createAiTool` factory and guardrails
- [Zod Schema Guide](../standards/zod-schema-guide.md) - Tool input schema patterns
- [Observability](observability.md) - Spans/events via `@/lib/telemetry/*` around AI calls
- `src/ai/models/registry.ts` (BYOK registry)
- `src/app/api/*` route handlers for per-request routing
