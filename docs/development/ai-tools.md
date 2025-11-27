# AI SDK v6 Tool Creation

Patterns for creating AI SDK v6 tools with guardrails (caching, rate limiting, telemetry) in TripSage AI.

## Overview

TripSage tools use the `createAiTool` factory from `@ai/lib/tool-factory`:

- **Type-safe tool creation** compatible with AI SDK v6 `Tool<InputValue, OutputValue>` types
- **Built-in guardrails**: caching, rate limiting, and telemetry
- **Consistent error handling** via `createToolError` utilities
- **Workflow-specific telemetry** for agent-level observability

For provider configuration (Gateway/BYOK), see [AI Integration](ai-integration.md).  
For tool input schema patterns, see [Zod Schema Guide](zod-schema-guide.md).

## Tool Creation Patterns

### Simple Tool (No Guardrails)

Use the AI SDK `tool()` helper for lightweight tools without guardrails:

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
    query: z.string().describe("Search query for LLM"),
  }),
});
```

### Tool with Guardrails (Recommended)

Use `createAiTool` for production tools that need caching, rate limiting, and telemetry:

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
    id: z.string().describe("Resource identifier"),
    userId: z.string().optional().describe("User context"),
  }),
  name: "myTool",
});
```

## Tool Execution Signature

All tool `execute` functions follow this signature:

```typescript
type ToolExecute<InputValue, OutputValue> = (
  params: InputValue,
  callOptions: ToolCallOptions
) => Promise<OutputValue>;
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `params` | `InputValue` | Validated input matching the tool's `inputSchema` |
| `callOptions.messages` | `ModelMessage[]` | Conversation messages for context extraction |
| `callOptions.toolCallId` | `string` | Unique identifier for this tool invocation |

**Return type**: Must be `Promise<OutputValue>` (even for synchronous operations).

## Guardrails Configuration

### Caching

Caching uses Upstash Redis via `@/lib/cache/upstash`. See [Observability](observability.md) for cache-related telemetry.

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

Rate limiting uses Upstash Redis with sliding window algorithm. Limits are enforced via `@upstash/ratelimit`.

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

Telemetry uses OpenTelemetry spans via `@/lib/telemetry/span`. See [Observability](observability.md) for span patterns.

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

## Agent Tool Wrappers

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

1. **Use `createAiTool`** for tools that need guardrails (caching, rate limiting, telemetry)
2. **Use `hashInput: true`** for cache keys when inputs are complex objects
3. **Include workflow telemetry** when tools are used in agents
4. **Accept `ToolCallOptions`** in all execute functions, even if unused
5. **Use shared utilities**:
   - `hashInputForCache` from `@/lib/cache/hash` for consistent hashing
   - `getCachedJson`/`setCachedJson` from `@/lib/cache/upstash` for caching
   - `createToolError` from `@ai/tools/server/errors` for standardized errors
6. **Type safety**: Use Zod schemas for input validation and type inference
7. **Server-only**: Include `import "server-only"` for tools that access secrets or external APIs

## Tool Input Schemas

Tool input schemas must follow AI SDK v6 patterns. See [Zod Schema Guide](zod-schema-guide.md) for full details.

**Requirements:**

- `z.strictObject()` for tool inputs
- `.describe()` on all fields for LLM comprehension
- `.nullable()` instead of `.optional()` for OpenAI strict mode

```typescript
export const toolInputSchema = z.strictObject({
  field: z.string().describe("Field description for LLM"),
  optionalField: z.number().nullable().describe("Nullable field for strict mode"),
});
```

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

Tools should be tested through AI SDK patterns. See `frontend/src/ai/lib/__tests__/tool-factory.test.ts` for examples:

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

**Test setup:**

- Mock Upstash Redis using `setupUpstashMocks()` from `@/test/setup/upstash`
- Use MSW handlers from `@/test/msw/handlers/upstash` for rate limiting
- Stub telemetry spans with `vi.mock("@/lib/telemetry/span")`

## Tool Catalog

All tools are exported from `frontend/src/ai/tools/index.ts`. The `toolRegistry` object provides typed access for agents.

### Search & Discovery

| Tool | Description | Source |
|------|-------------|--------|
| `webSearch` | Web search via Firecrawl v2.5 | `server/web-search.ts` |
| `webSearchBatch` | Batch web search for multiple queries | `server/web-search-batch.ts` |
| `crawlUrl` / `crawlSite` | Web crawling and content extraction | `server/web-crawl.ts` |
| `searchActivities` | Activity search via Google Places | `server/activities.ts` |
| `getActivityDetails` | Activity details by Place ID | `server/activities.ts` |
| `lookupPoiContext` | POI context via Google Places | `server/google-places.ts` |

### Travel Planning

| Tool | Description | Source |
|------|-------------|--------|
| `searchFlights` | Flight search | `server/flights.ts` |
| `searchAccommodations` | Accommodation search | `server/accommodations.ts` |
| `getAccommodationDetails` | Accommodation details | `server/accommodations.ts` |
| `checkAvailability` | Check accommodation availability | `server/accommodations.ts` |
| `bookAccommodation` | Book accommodation (requires approval) | `server/accommodations.ts` |
| `getTravelAdvisory` | Travel safety scores | `server/travel-advisory.ts` |
| `getCurrentWeather` | Weather lookup | `server/weather.ts` |

### Planning & Itinerary

| Tool | Description | Source |
|------|-------------|--------|
| `createTravelPlan` | Create new travel plan | `server/planning.ts` |
| `saveTravelPlan` | Save travel plan | `server/planning.ts` |
| `updateTravelPlan` | Update existing plan | `server/planning.ts` |
| `deleteTravelPlan` | Delete travel plan | `server/planning.ts` |
| `combineSearchResults` | Combine search results from multiple sources | `server/planning.ts` |

### Calendar & Scheduling

| Tool | Description | Source |
|------|-------------|--------|
| `createCalendarEvent` | Create Google Calendar event | `server/calendar.ts` |
| `getAvailability` | Check calendar free/busy | `server/calendar.ts` |
| `exportItineraryToIcs` | Export events to ICS format | `server/calendar.ts` |

### Memory & Context

| Tool | Description | Source |
|------|-------------|--------|
| `addConversationMemory` | Store conversation memory | `server/memory.ts` |
| `searchUserMemories` | Search user memory | `server/memory.ts` |

### Maps & Location

| Tool | Description | Source |
|------|-------------|--------|
| `geocode` | Address to coordinates | `server/maps.ts` |
| `distanceMatrix` | Distance/duration between locations | `server/maps.ts` |

### Human-in-the-Loop

| Tool | Description | Source |
|------|-------------|--------|
| `requireApproval` | Request user approval | `server/approvals.ts` |
| `getApprovalStatus` | Check approval status | `server/approvals.ts` |
| `grantApproval` | Grant pending approval | `server/approvals.ts` |
| `denyApproval` | Deny pending approval | `server/approvals.ts` |

## Error Codes Reference

Tool errors use standardized codes from `@ai/tools/server/errors.ts`. Use `createToolError()` to construct errors and `isToolError()` to check error types.

### General Errors

| Code | Constant | Description |
|------|----------|-------------|
| `invalid_params` | `invalidParams` | Invalid input parameters |
| `tool_execution_failed` | `toolExecutionFailed` | Generic execution failure |
| `tool_rate_limited` | `toolRateLimited` | Rate limit exceeded |

### Web Search Errors

| Code | Constant | Description |
|------|----------|-------------|
| `web_search_not_configured` | `webSearchNotConfigured` | Missing API key |
| `web_search_rate_limited` | `webSearchRateLimited` | Rate limit exceeded |
| `web_search_unauthorized` | `webSearchUnauthorized` | Invalid API key |
| `web_search_payment_required` | `webSearchPaymentRequired` | Payment required |
| `web_search_failed` | `webSearchFailed` | Search failed |
| `web_search_error` | `webSearchError` | General error |

### Accommodation Errors

| Code | Constant | Description |
|------|----------|-------------|
| `accom_search_not_configured` | `accomSearchNotConfigured` | Missing configuration |
| `accom_search_rate_limited` | `accomSearchRateLimited` | Rate limit exceeded |
| `accom_search_unauthorized` | `accomSearchUnauthorized` | Unauthorized |
| `accom_search_timeout` | `accomSearchTimeout` | Request timeout |
| `accom_search_failed` | `accomSearchFailed` | Search failed |
| `accom_details_not_found` | `accomDetailsNotFound` | Accommodation not found |
| `accom_booking_failed` | `accomBookingFailed` | Booking failed |
| `accom_booking_session_required` | `accomBookingSessionRequired` | Session required |

### Approval Errors

| Code | Constant | Description |
|------|----------|-------------|
| `approval_required` | `approvalRequired` | User approval required |
| `approval_missing_session` | `approvalMissingSession` | No session for approval |
| `approval_backend_unavailable` | `approvalBackendUnavailable` | Approval service unavailable |

### Error Handling Example

```typescript
import { createToolError, isToolError, TOOL_ERROR_CODES } from "@ai/tools/server/errors";

// Throwing errors
if (!apiKey) {
  throw createToolError(TOOL_ERROR_CODES.webSearchNotConfigured);
}

// With message and metadata
throw createToolError(
  TOOL_ERROR_CODES.webSearchFailed,
  "Search timed out after 30s",
  { query: params.query, timeout: 30000 }
);

// Checking errors
try {
  await searchTool.execute(params, callOptions);
} catch (error) {
  if (isToolError(error)) {
    // Handle known tool error
    console.log(`Tool error: ${error.code}`);
  }
  throw error;
}
```

## Real-World Example

See [Activities Developer Guide](activities.md) for a complete implementation example with:

- Search and details tools using `createAiTool`
- Google Places API integration
- Supabase-backed caching
- Rate limiting and telemetry

## Related Documentation

- [AI Integration](ai-integration.md) - Gateway/BYOK provider configuration
- [Zod Schema Guide](zod-schema-guide.md) - Tool input schema patterns
- [Observability](observability.md) - Telemetry spans and logging
- [Activities](activities.md) - Real-world tool implementation example
- [Testing](testing.md) - Test patterns and MSW handlers

## Source Files

- Tool Factory: `frontend/src/ai/lib/tool-factory.ts`
- Tool Registry: `frontend/src/ai/tools/index.ts`
- Error Codes: `frontend/src/ai/tools/server/errors.ts`
- AI SDK v6 Documentation: <https://sdk.vercel.ai/docs>
