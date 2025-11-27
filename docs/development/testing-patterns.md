# Testing Patterns and Decision Framework

Reference companion to `docs/development/testing-guide.md`. Use this as a quick chooser for patterns and helpers.

## Test-Type Decision Table

| Scenario | Recommended Test Type | Key Tools |
| --- | --- | --- |
| Pure functions, selectors, reducers | Unit | Plain asserts; no MSW |
| Hooks with DOM/React state only | Component (jsdom) | RTL `renderHook`; factories |
| Hooks/services calling HTTP | Component or Integration | MSW handlers; `createMockQueryClient` when React Query involved |
| Next.js route handlers | API (node) | MSW for upstreams; `createMockNextRequest` |
| Multi-module flow (store + hook + API) | Integration | MSW + real providers |
| Browser-only flows | E2E (Playwright) | Keep minimal set |

## Mocking Strategy

1. **Network:** MSW 2 handlers (`frontend/src/test/msw/handlers/*`); never `vi.mock("node-fetch")`. Use MSW for network mocking instead of mocking fetch/HTTP libraries directly, as MSW provides request-level interception that works across test types.
2. **AI SDK:** `MockLanguageModelV3`, `simulateReadableStream` (`frontend/src/test/ai-sdk/*`).
3. **React Query:** `createMockQueryClient`, `createControlledQuery/Mutation` (`frontend/src/test/query-mocks.tsx`); otherwise wrap in `QueryClientProvider`.
4. **Supabase:** `frontend/src/test/mocks/supabase.ts`; prefer MSW for REST RPCs.
5. **Timers:** `withFakeTimers` opt-in utility.

## Example Snippets

### MSW Error Path

```ts
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";

server.use(http.get("https://api.example.com/items", () => HttpResponse.json({ error: "fail" }, { status: 500 })));
```

### AI SDK Tool Assertion

```ts
import { z } from "zod";
import { streamText } from "ai";
import { createMockModelWithTracking } from "@/test/ai-sdk/mock-model";

const tools = {
  enrich: {
    execute: ({ id }: { id: string }) => `ok:${id}`,
    parameters: z.strictObject({ id: z.string() }),
  },
};

// Wrap the mock model so tool calls are recorded
const { model, calls } = createMockModelWithTracking();

const result = await streamText({
  messages: [{ role: "user", content: "hi" }],
  model,
  tools,
});

// Assert on tracked tool call
expect(calls[0]?.toolName).toBe("enrich");
expect(calls[0]?.args).toEqual({ id: expect.any(String) });

// Or inspect the streamed response content
const toolCalls = result.response.messages.flatMap((m) =>
  m.content.filter((c) => c.type === "tool-call")
);
expect(toolCalls[0]?.name).toBe("enrich");
expect(toolCalls[0]?.args).toMatchObject({ id: expect.any(String) });
```

### React Query Controlled Query

```ts
import { createControlledQuery, createMockQueryClient } from "@/test/query-mocks";

const { controller, query } = createControlledQuery<string, Error>();
const client = createMockQueryClient();
// inject query into hook under test as needed; drive states via controller.triggerSuccess("data")
```

### Fake Timers

```ts
import { withFakeTimers } from "@/test/utils/with-fake-timers";

it("retries after delay", withFakeTimers(async () => {
  await action();
  vi.advanceTimersByTime(1000);
  expect(retrySpy).toHaveBeenCalled();
}));
```

## Performance Notes

- Use threads pool (`vitest --pool=threads`) locally and in CI.
- Keep handler data minimal; avoid large JSON fixtures.
- Prefer factories over inline objects to reduce duplication.
- For slow tests, run `vitest run --project=<name> --inspect` and profile.

## Anti-Patterns to Avoid

- `vi.mock()` for HTTP/fetch; use MSW instead.
- Global fake timers.
- Snapshot tests for highly dynamic components.
- Sharing QueryClient instances across tests without reset.
- Leaving handlers registered between tests (always rely on `server.resetHandlers()`).
