# AI integration with Vercel AI SDK v7

Patterns and options for configuring providers via the Vercel AI Gateway and direct keys.

## Gateway `providerOptions`

Use `providerOptions.gateway` in `streamText`/`generateText` calls when the resolved model is a Gateway model (user or team scoped). Keep routing logic in route handlers, not in the registry.

## Model Policy

Model profiles and token ceilings are centralized in `src/lib/tokens/limits.ts`; `src/ai/models/defaults.ts` owns the default profile selections and re-exports the profile table for provider code.

- `standard`: `openai/gpt-5.4-mini` via Gateway, `gpt-5.4-mini` for direct OpenAI.
- `planning`: `openai/gpt-5.5` via Gateway, `gpt-5.5` for direct OpenAI.
- `utility`: `openai/gpt-5.4-nano` via Gateway, `gpt-5.4-nano` for direct OpenAI.
- Anthropic has no implicit app-owned default. Users/admins must pick a current provider-owned model from their catalog; key validation probes Anthropic's model catalog instead of hard-coding a Claude model.

User OpenAI BYOK uses direct OpenAI Responses API models so user-owned keys fail closed instead of falling back to team credentials. App-owned traffic uses Vercel AI Gateway when the user has opted into team fallback.

## Provider V4 resolution

The server-only registry returns Provider V4 models directly:

- Vercel AI Gateway returns its native Provider V4 model
- OpenAI BYOK uses `.responses()`
- OpenRouter uses the OpenAI-compatible `.chat()` surface
- Anthropic uses `.languageModel()`
- xAI uses `.chat()` explicitly to preserve chat-completions behavior

Do not add a model coercion adapter. Provider factories already enforce the shared contract.

### Prefer OpenAI Gateway endpoints

```ts
const result = await streamText({
  model,
  messages,
  providerOptions: {
    gateway: { only: ["openai"] },
  },
});
```

### Cost-conscious standard routing

```ts
const result = await streamText({
  model,
  messages,
  providerOptions: {
    gateway: {
      models: ["openai/gpt-5.4-mini"],
      tags: ["profile:standard"],
    },
  },
});
```

### Escalate complex planning explicitly

```ts
const result = await streamText({
  model,
  messages,
  providerOptions: {
    gateway: {
      models: ["openai/gpt-5.5"],
      tags: ["profile:planning"],
    },
  },
});
```

## Best Practices

- Keep `providerOptions` close to route handlers (avoid encoding in the provider registry).
- Pair routing with per-request token budgets and chat limits.
- Use AI SDK timeout configuration (`timeout: { totalMs, stepMs }`) to cap total and per-step
  latency for streaming and tool loops.
- Prefer Gateway API keys (`AI_GATEWAY_API_KEY`) for app-owned routing. User BYOK keys stay direct and fail closed when provider validation fails.
- Tests: use `MockLanguageModelV4` and assert `providerOptions` on recorded calls.
- Before changing defaults, run `pnpm test:ai-model-smoke -- --models=openai/gpt-5.4-mini,openai/gpt-5.4-nano,openai/gpt-5.5 --json` with a non-production `AI_GATEWAY_API_KEY`.

## AI SDK v7 canonical patterns

### Core `streamText` route handler

```ts
import {
  convertToModelMessages,
  createUIMessageStreamResponse,
  streamText,
  toUIMessageStream,
} from "ai";
import type { UIMessage } from "ai";

export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json();
  const result = streamText({
    model,
    messages: await convertToModelMessages(messages),
    tools,
  });

  const stream = toUIMessageStream({
    stream: result.stream,
    originalMessages: messages,
    onError: (error) => (error instanceof Error ? error.message : "unknown_error"),
    messageMetadata: ({ part }) => {
      if (part.type === "start") return { sessionId: "server-session-id" };
      if (part.type === "finish") return { tokens: part.totalUsage?.totalTokens ?? 0 };
      return undefined;
    },
  });

  return createUIMessageStreamResponse({ stream });
}
```

`ToolLoopAgent` endpoints use the shared `createAgentRoute()` factory, which
returns the native `createAgentUIStreamResponse()` response. The memory agent
uses the core stream helper pair shown above.

### Client hook (useChat)

- Use `DefaultChatTransport` for static headers/body/credentials.
- Use `sendMessage(..., { headers, body, metadata })` for per-request overrides.
- Do not pass `headers` or `body` in `useChat` options. Put static values in `DefaultChatTransport` and per-request values in `sendMessage()`.

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

- **Duplicate assistant messages**: pass `originalMessages` to `toUIMessageStream()`.
- **Provider options**: `UIMessage` does not carry provider options. Use
  `convertToModelMessages()` with call options or inject options in the route handler.
- **Trusted instructions**: pass static, server-owned prompts through `instructions`. Do not accept user-controlled system messages or interpolate request values into privileged instructions; keep validated request parameters in the user message.
- **Client message boundary**: reconstruct submitted user messages from approved text/file fields before persistence or model conversion. Strip client provider references and provider metadata/options so shared provider credentials cannot resolve client-selected provider resources.
- **Memory trust boundary**: keep retrieved memory out of `instructions`. Encode bounded memory as a JSON `memoryContext` user message immediately before the latest user request; static instructions declare that field untrusted reference data.
- **Lifecycle callbacks**: use `onEnd` and `onStepEnd` for Core generation and agents. `useChat` keeps its native `onFinish` callback.

## Timeouts

AI SDK v7 supports per-call timeouts with optional per-step limits. Prefer `timeout`
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

Use AI SDK v7 UI message metadata and data parts to expose model usage, finish
reason, and transient status updates to the client.

- Schemas live in `src/domain/schemas/ai.ts` (`chatMessageMetadataSchema`,
  `agentMessageMetadataSchema`, `chatDataPartSchemas`).
- Client: pass `messageMetadataSchema` + `dataPartSchemas` to `useChat`.
- Server: attach metadata via `messageMetadata` in `toUIMessageStream()`, and
  stream transient data parts via `createUIMessageStream` + `writer.write`.
- Enable `sendSources: true` to include `source-url` parts for citations.

### Reasoning files

- Keep a `reasoning-file` part only when `mediaType` and `url` pass validation.
- Accept `http`, `https`, or matching valid base64 data URLs.
- Render through the safe attachment path. Never render a data URL directly.
- Add only `[reasoning-file:<mediaType>]` to token-budget text.

## Provider Metadata During Tool Input Streaming

AI SDK v7 provider-executed tools, such as Model Context Protocol (MCP) tools, can attach
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
