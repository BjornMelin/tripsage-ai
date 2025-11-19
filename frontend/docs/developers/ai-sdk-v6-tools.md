# AI SDK v6 Tool Creation Guide

This guide documents the canonical patterns for creating AI SDK v6 tools with guardrails (caching, rate limiting, telemetry) in TripSage AI.

## Overview

All tools in TripSage AI use the `createAiTool` factory from `@ai/lib/tool-factory`. This factory provides:

- **Type-safe tool creation** compatible with AI SDK v6 `Tool<InputValue, OutputValue>` types
- **Built-in guardrails**: caching, rate limiting, and telemetry
- **Consistent error handling** via `createToolError` utilities
- **Workflow-specific telemetry** for agent-level observability

## Basic Tool Creation

### Simple Tool (No Guardrails)

```typescript
import type { ToolCallOptions } from "ai";
import { tool } from "ai";
import { z } from "zod";

export const myTool = tool({
  description: "A simple tool description",
  execute: async (params, callOptions?: ToolCallOptions) => {
    // Tool implementation
    return { result: "ok" };
  },
  inputSchema: z.object({
    query: z.string(),
  }),
});
```

### Tool with Guardrails (Recommended)

```typescript
import "server-only";

import type { ToolCallOptions } from "ai";
import { z } from "zod";
import { createAiTool } from "@ai/lib/tool-factory";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";

export const myTool = createAiTool({
  description: "A tool with guardrails",
  execute: async (params, callOptions?: ToolCallOptions) => {
    // Tool implementation
    return { result: "ok" };
  },
  guardrails: {
    cache: {
      hashInput: true,
      key: (params) => `my-tool:${params.id}`,
      namespace: "tool:my-tool",
      ttlSeconds: 60 * 30, // 30 minutes
    },
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.webSearchRateLimited,
      identifier: (params, callOptions) => {
        // Extract user ID from callOptions.messages or params
        return params.userId ?? "anonymous";
      },
      limit: 20,
      prefix: "ratelimit:tool:my-tool",
      window: "1 m",
    },
    telemetry: {
      workflow: "myWorkflow", // Optional: for agent-level telemetry
      attributes: (params) => ({
        customAttribute: params.someField,
      }),
      redactKeys: ["sensitiveField"],
    },
  },
  inputSchema: z.object({
    id: z.string(),
    userId: z.string().optional(),
  }),
  name: "myTool",
});
```

## Tool Execution Signature

All tool `execute` functions must follow this signature:

```typescript
type ToolExecute<InputValue, OutputValue> = (
  params: InputValue,
  callOptions: ToolCallOptions
) => Promise<OutputValue>;
```

**Key points:**

- **`params`**: Validated input matching the tool's `inputSchema`
- **`callOptions`**: AI SDK v6 context containing:
  - `messages`: Array of `ModelMessage` from the conversation
  - `toolCallId`: Unique identifier for this tool call
- **Return type**: Must be `Promise<OutputValue>` (even for synchronous operations)

## Guardrails Configuration

### Caching

```typescript
cache: {
  // Required: function that generates cache key suffix
  key: (params) => `user-${params.userId}`,
  
  // Optional: namespace prefix (defaults to `tool:${name}`)
  namespace: "custom:namespace",
  
  // Optional: hash input using SHA-256 for cache key (recommended for complex inputs)
  hashInput: true,
  
  // Optional: serialize result before caching
  serialize: (result, params) => ({ ...result, cachedAt: Date.now() }),
  
  // Optional: deserialize cached payload
  deserialize: (payload, params) => payload as MyResultType,
  
  // Optional: transform cached value before returning
  onHit: (cached, params, meta) => ({
    ...cached,
    fromCache: true,
    tookMs: Date.now() - meta.startedAt,
  }),
  
  // Optional: bypass cache for specific requests
  shouldBypass: (params) => Boolean(params.fresh),
  
  // Optional: TTL in seconds (number or function)
  ttlSeconds: 60 * 30, // or (params, result) => calculateTtl(params, result)
}
```

### Rate Limiting

```typescript
rateLimit: {
  // Required: error code to throw when limit exceeded
  errorCode: TOOL_ERROR_CODES.webSearchRateLimited,
  
  // Required: function that returns identifier for rate limiting
  // Can use params and/or callOptions.messages
  identifier: (params, callOptions) => {
    // Extract user ID from messages or params
    return params.userId ?? extractUserIdFromMessages(callOptions.messages);
  },
  
  // Required: sliding window limit
  limit: 20,
  
  // Required: sliding window duration (e.g., "1 m", "5 m", "1 h")
  window: "1 m",
  
  // Optional: prefix override (defaults to `ratelimit:tool:${name}`)
  prefix: "ratelimit:custom:prefix",
}
```

### Telemetry

```typescript
telemetry: {
  // Optional: custom span name suffix (defaults to tool name)
  name: "customSpanName",
  
  // Optional: build custom attributes from params
  attributes: (params) => ({
    customField: params.someValue,
    count: params.items?.length ?? 0,
  }),
  
  // Optional: keys to redact from telemetry spans
  redactKeys: ["apiKey", "password", "token"],
  
  // Optional: workflow identifier for agent-level telemetry
  workflow: "itineraryPlanning", // or "destinationResearch", "budgetPlanning", etc.
}
```

## Using Tools in Agents

When creating agent-specific tool wrappers, use `createAiTool` to add workflow telemetry:

```typescript
import { createAiTool } from "@ai/lib/tool-factory";
import { toolRegistry } from "@ai/tools";

function buildMyAgentTools(identifier: string): ToolSet {
  const baseTool = toolRegistry.myTool as unknown as {
    execute?: (params: unknown, callOptions?: unknown) => Promise<unknown> | unknown;
  };

  const wrappedTool = createAiTool({
    description: baseTool.description ?? "My tool",
    execute: async (params, callOptions) => {
      if (typeof baseTool.execute !== "function") {
        throw new Error("Tool missing execute binding");
      }
      const result = baseTool.execute(params, callOptions);
      return result instanceof Promise ? result : Promise.resolve(result);
    },
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:my-agent:my-tool",
        namespace: "agent:my-agent:my-tool",
        ttlSeconds: 60 * 30,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.webSearchRateLimited,
        identifier: () => identifier,
        limit: 10,
        prefix: "ratelimit:agent:my-agent:my-tool",
        window: "1 m",
      },
      telemetry: {
        workflow: "myAgentWorkflow",
      },
    },
    inputSchema: myToolInputSchema,
    name: "agentMyTool",
  });

  return { myTool: wrappedTool } satisfies ToolSet;
}
```

## Best Practices

1. **Always use `createAiTool`** for tools that need guardrails (caching, rate limiting, telemetry)
2. **Use `hashInput: true`** for cache keys when inputs are complex objects
3. **Include workflow telemetry** when tools are used in agents
4. **Accept `ToolCallOptions`** in all execute functions, even if unused
5. **Use shared utilities**:
   - `hashInputForCache` from `@/lib/cache/hash` for consistent hashing
   - `getCachedJson`/`setCachedJson` from `@/lib/cache/upstash` for caching
   - `createToolError` from `@/lib/tools/errors` for standardized errors
6. **Type safety**: Use Zod schemas for input validation and type inference

## Migration from Legacy Patterns

### Before (Legacy)

```typescript
export const myTool = tool({
  execute: async (params) => {
    // Manual caching, rate limiting, telemetry
    return result;
  },
});
```

### After (AI SDK v6)

```typescript
export const myTool = createAiTool({
  execute: async (params, callOptions) => {
    // Guardrails handled automatically
    return result;
  },
  guardrails: {
    cache: { /* ... */ },
    rateLimit: { /* ... */ },
    telemetry: { /* ... */ },
  },
});
```

## Testing Tools

Tools should be tested through AI SDK patterns. See `frontend/src/lib/ai/tool-factory.test.ts` for examples:

```typescript
import type { ToolCallOptions } from "ai";
import { beforeEach, describe, expect, test, vi } from "vitest";

const callOptions: ToolCallOptions = {
  messages: [],
  toolCallId: "test-call",
};

test("tool caches results", async () => {
  const result1 = await myTool.execute?.({ id: "abc" }, callOptions);
  const result2 = await myTool.execute?.({ id: "abc" }, callOptions);
  // Second call should use cache
});
```

## References

- AI SDK v6 Documentation: <https://sdk.vercel.ai/docs>
- Tool Factory: `frontend/src/lib/ai/tool-factory.ts`
- Tool Registry: `frontend/src/lib/tools/index.ts`
- Error Codes: `frontend/src/lib/tools/errors.ts`
