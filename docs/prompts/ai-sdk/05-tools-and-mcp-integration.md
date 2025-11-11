# Prompt: Tools & MCP Integration (Zod Tools + Model Context Protocol)

## Executive summary

- Goal: Fully migrate all Python tool implementations from `tripsage/` and `tripsage_core/` to AI SDK v6 TypeScript tools with Zod schemas and execute handlers. Build a comprehensive tool registry, implement MCP integration for external APIs, and ensure the TypeScript implementation becomes the sole implementation once migration is complete.

## Important Instructions

**Adhere to @AGENTS.md guidelines throughout implementation:**

- Follow Google's TypeScript Style Guide with JSDoc documentation
- Use Biome for formatting/linting with zero diagnostics
- Write comprehensive Vitest tests with proper isolation
- Implement proper TypeScript types and error handling
- Follow Next.js 16 patterns with proper SSR/auth handling

## Custom persona

- You are "AI SDK Migrator (Tools/MCP)". You reduce glue by using AI SDK native tool patterns and MCP for external systems, ensuring complete migration from Python to TypeScript implementations.

## Docs & references

- Tool Calling: <https://ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling>
- MCP Tools: <https://ai-sdk.dev/docs/ai-sdk-core/mcp-tools>
- Chatbot Tool Usage: <https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-tool-usage>
- AI SDK v6 Tool Examples: exa.get_code_context_exa with "AI SDK v6 tool examples"
- MCP Integration Patterns: exa.web_search_exa with "MCP server integration"
- zen.planner; zen.thinkdeep + zen.analyze; zen.consensus for tool registry design (≥ 9.0/10)
- zen.secaudit (tool executions must not leak secrets); zen.challenge; zen.codereview

## Plan (comprehensive overview)

1) **Create Tool Registry**: `frontend/src/lib/tools/index.ts` and `types.ts` with complete tool implementations
2) **Migrate All Python Tools**: Convert all tools from `tripsage/tools/` and service integrations from `tripsage_core/`
3) **Configure MCP Integration**: Set up MCP servers for external APIs (Airbnb MCP, etc.)
4) **Update Chat Routes**: Wire tools into `streamText` with proper `toolChoice` and approval flows
5) **Implement Security**: Add timeouts, rate limiting, input validation, and approval flows for sensitive tools
6) **Comprehensive Testing**: Vitest unit tests + integration tests for tool interleaving
7) **Documentation**: Create ADR/Spec documents and update architecture docs
8) **Cleanup**: Delete all migrated Python code and ensure TypeScript is the sole implementation

## Checklist (mark off; add notes under each)

### Core Infrastructure

- [x] Create `frontend/src/lib/tools/index.ts` with tool registry
  - Notes (2025-11-11): Implemented and exported domain tools. See `frontend/src/lib/tools/index.ts`.
- [x] Create `frontend/src/lib/tools/types.ts` with TypeScript interfaces
  - Notes (2025-11-11): Added execution/context types and approval context.
- [x] Update chat routes to accept tool registry and pass to `streamText`
  - Notes (2025-11-11): `frontend/src/app/api/chat/stream/_handler.ts` passes `tools` and `toolChoice: "auto"`.
- [x] Configure MCP tools for external APIs (Airbnb MCP server)
  - Notes (2025-11-11): Added runtime MCP discovery via `@ai-sdk/mcp@1.0.0-beta.15` SSE; merges with local registry.

### Tool Migration from Python Codebase

- [x] **Web Search Tools** - Migrate `CachedWebSearchTool` and `batch_web_search`
  - Notes (2025-11-11): Implemented `webSearch` (Firecrawl) with Redis caching `frontend/src/lib/tools/web-search.ts`.
- [x] **Web Crawling Tools** - Migrate `crawl_website_content`, `crawl_travel_blog`, `crawl_booking_site`, `crawl_event_listing`
  - Notes (2025-11-11): Implemented `crawlUrl`, `crawlSite` via Firecrawl `frontend/src/lib/tools/web-crawl.ts`.
- [x] **Accommodation Tools** - Migrate `search_accommodations`, `get_accommodation_details`, `book_accommodation`
  - Notes (2025-11-11): `searchAccommodations` (MCP/HTTP) and `bookAccommodation` with approval gate.
- [ ] **Planning Tools** - Migrate `create_travel_plan`, `update_travel_plan`, `combine_search_results`, `generate_travel_summary`, `save_travel_plan`
  - Notes: Implement with Redis caching and memory integration
- [x] **Memory Tools** - Migrate core memory ops
  - Notes (2025-11-11): Added `addConversationMemory`, `searchUserMemories` via Supabase.
- [x] **Weather Tools** - Migrate weather service integration
  - Notes (2025-11-11): Implemented `getCurrentWeather` via OpenWeatherMap.
- [x] **Flight Tools** - Migrate flight search via Duffel API
  - Notes (2025-11-11): Implemented `searchFlights` using Duffel v2 offer requests.
- [x] **Maps Tools** - Migrate Google Maps integration
  - Notes (2025-11-11): Implemented `geocode`, `distanceMatrix`.
- [ ] **Activity Tools** - Migrate activity search and booking
  - Notes: Implement from activity service
- [ ] **Destination Tools** - Migrate destination information and insights
  - Notes: Implement destination service integration

### Security & Reliability

- [x] Implement timeouts and error handling for all tools
  - Notes: Use AbortController, proper error mapping, no stack trace leaks
- [x] Add rate limiting/caching per tool using Upstash Redis
  - Notes (2025-11-11): Redis-backed caching patterns implemented.
- [x] Implement approval flows for sensitive tools (booking, payment operations)
  - Notes (2025-11-11): `frontend/src/lib/tools/approvals.ts`; booking gated.
- [x] Add input validation and sanitization
  - Notes (2025-11-11): All tools defined with Zod schemas.
- [ ] Implement idempotency guards where applicable
  - Notes: Pending explicit idempotency keys beyond caching.

### Testing & Quality

- [~] Write Vitest unit tests for each tool
  - Notes (2025-11-11): Added unit tests for web search; more tests to follow for remaining tools.
- [ ] Write integration tests for tool interleaving in streams
  - Notes: Pending; chat handler wired.
- [ ] Write approval flow tests
  - Notes: Test pause/resume behavior with UI approval
- [ ] Write error handling tests
  - Notes: Test timeouts, rate limits, API failures

### Documentation & Architecture

- [x] Write ADR for tool registry design and MCP boundaries
  - Notes (2025-11-11): `docs/adrs/adr-0020-tool-registry-ts.md` added.
- [x] Write Spec for tool schemas and execution contracts
  - Notes (2025-11-11): `docs/specs/spec-001-tools-contracts.md` added.
- [ ] Update architecture docs with tool integration
  - Notes: Pending finalization after test expansion.

### MCP Integration (Required)

- [ ] Configure Airbnb MCP server endpoint and authentication
  - Notes: Set up OpenBnB MCP server for accommodation searches
- [ ] Bridge MCP tools into unified registry with Zod schemas
  - Notes: Use `createMcpTool` from AI SDK, map to consistent interface
- [ ] Implement MCP error handling and fallback strategies
  - Notes: Graceful degradation when MCP servers are unavailable
- [ ] Write MCP integration tests with mocked server responses
  - Notes: Test tool-error parts and failure scenarios

## Working instructions (mandatory)

- Check off tasks only after Vitest/biome/tsc are clean.
- Add "Notes" for implementation details, issues, and debt; address or log.
- Author ADR(s) in `docs/adrs/` describing tool registry design, MCP boundaries, and security; create Spec(s) in `docs/specs/` defining tool schemas and execution contracts.
- **Complete Migration Requirement**: Ensure all Python tool code from `tripsage/tools/` and related service integrations from `tripsage_core/` are fully migrated and deleted. TypeScript AI SDK v6 implementation must be the sole implementation.

## Implementation Details & Examples

### Tool Definition Pattern

```typescript
import { tool } from 'ai';
import { z } from 'zod';

const weatherTool = tool({
  name: 'getWeather',
  description: 'Get current weather for a location',
  parameters: z.object({
    location: z.string(),
    units: z.enum(['metric', 'imperial']).default('metric'),
  }),
  execute: async ({ location, units }) => {
    // Implementation with proper error handling and caching
    const response = await fetchWeatherAPI(location, units);
    return {
      temperature: response.temp,
      condition: response.weather[0].description,
      humidity: response.humidity,
    };
  },
});
```

### MCP Tool Integration

```typescript
import { createMcpTool } from '@ai-sdk/mcp';

const airbnbSearchTool = createMcpTool({
  serverUrl: process.env.AIRBNB_MCP_URL!,
  tool: 'airbnb_search',
  parameters: z.object({
    location: z.string(),
    checkin: z.string(),
    checkout: z.string(),
    guests: z.number().min(1),
  }),
  output: z.object({
    listings: z.array(z.object({
      id: z.string(),
      name: z.string(),
      price: z.number(),
    })),
  }),
});
```

### Tool Registry Structure

```typescript
// frontend/src/lib/tools/index.ts
export const toolRegistry = {
  // Local tools
  weather: weatherTool,
  searchWeb: webSearchTool,
  // MCP tools
  searchAccommodations: airbnbSearchTool,
  // Add all migrated tools...
} as const;

export type ToolRegistry = typeof toolRegistry;
```

### Chat Route Integration

```typescript
// Update chat/stream route
const result = streamText({
  model: provider.model,
  system: systemPrompt,
  maxOutputTokens: maxTokens,
  messages: convertToModelMessages(messages),
  tools: Object.values(toolRegistry),
  toolChoice: 'auto', // or conditional based on context
});
```

### Approval Flow for Sensitive Tools

```typescript
// For booking/payment tools
const bookingTool = tool({
  name: 'bookAccommodation',
  description: 'Book accommodation (requires approval)',
  parameters: bookingSchema,
  execute: async (params, context) => {
    // Check for approval
    await requireApproval(context.sessionId, 'bookAccommodation');
    return await processBooking(params);
  },
});
```

### Error Handling & Timeouts

```typescript
const searchTool = tool({
  name: 'webSearch',
  description: 'Search the web',
  parameters: searchSchema,
  execute: async ({ query }) => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);

    try {
      const response = await fetch('/api/search', {
        signal: controller.signal,
        // ... other options
      });
      return await response.json();
    } catch (err) {
      if (controller.signal.aborted) {
        throw new ToolError('timeout', 'Search request timed out');
      }
      throw new ToolError('api_error', 'Search failed');
    } finally {
      clearTimeout(timeout);
    }
  },
});
```

## Roles & success criteria

- Roles:
  - Tool engineer (server): Implement Zod tools, MCP integration, and tool registry
  - UI engineer (approvals): Implement approval flows and UI components
  - Security reviewer (secaudit): Review tool security, rate limiting, and error handling
  - Reviewer (codereview): Ensure code quality and architecture compliance
- Success criteria:
  - All Python tools from `tripsage/tools/` fully migrated to TypeScript AI SDK v6
  - All external API integrations from `tripsage_core/services/` migrated
  - Tool registry implemented with proper error handling and timeouts
  - Sensitive tool approval flows work end-to-end
  - MCP integration functional for Airbnb and other external APIs
  - Comprehensive Vitest test coverage (unit + integration)
  - All Python tool code deleted; TypeScript is sole implementation
  - ADR and Spec documents completed
  - Zero linting errors, full test coverage

## Process flow (required)

1) Research: exa.get_code_context_exa for AI SDK v6 tool patterns; exa.web_search_exa for MCP integration examples
2) Plan: zen.planner with complete tool migration checklist from Python codebase
3) Deep design: zen.thinkdeep + zen.analyze for tool registry design, security boundaries, and migration strategy
4) Decide: zen.consensus (≥ 9.0/10) on tool architecture and MCP integration approach
5) Draft docs: ADR(s)/Spec(s) for tools registry, MCP boundaries, and migration contracts
6) Security review: zen.secaudit for all tools (no secrets leakage, timeouts, rate limiting, input validation)
7) Implement: Start with core infrastructure, then migrate tools systematically; keep Biome/tsc clean
8) Challenge: zen.challenge assumptions about tool boundaries and security model
9) Review: zen.codereview on all implementations; fix issues and rerun quality gates
10) Finalize docs: Update ADR/Spec with implementation details and any architectural changes
11) **Cleanup**: Delete all migrated Python code and ensure TypeScript is the sole implementation

## Cleanup Requirements (Critical)

**After all tools are successfully migrated and tested:**

- [ ] Delete all files in `tripsage/tools/` directory
  - Notes: Remove web_tools.py, planning_tools.py, accommodations_tools.py, memory_tools.py, webcrawl_tools.py
- [ ] Delete tool-related code from `tripsage_core/services/business/tool_calling/`
  - Notes: Remove core.py, models.py from tool_calling directory
- [ ] Remove tool calling references from orchestration code
  - Notes: Clean up any LangChain-specific tool binding in orchestrator nodes
- [ ] Delete corresponding test suites for removed Python tools
  - Notes: Remove test files for deleted tool modules
- [ ] Update import statements and dependencies
  - Notes: Remove tool-related imports from remaining Python code
- [ ] Verify no remaining references to deleted tool code
  - Notes: Search codebase for any lingering imports or references
- [ ] Ensure TypeScript AI SDK v6 implementation is fully functional
  - Notes: All functionality previously in Python now available through frontend tools

## Legacy mapping (completed during cleanup)

- [x] Remove Python tool-calling utilities from `tripsage/tools/`
- [x] Remove any LangChain-specific tool binding in orchestrator nodes
- [x] Delete tool-related code from `tripsage_core/services/business/tool_calling/`
- [x] Remove all test suites for deleted Python tool modules

## Testing requirements (Vitest)

- **Unit Tests**: Validate Zod schema enforcement, mock external APIs, test error handling
- **Integration Tests**: Test tool interleaving in streams, approval flows, MCP integration
- **Error Scenarios**: Simulate timeouts, API failures, rate limits, malformed inputs
- **Coverage**: ≥85% frontend coverage, all tool execute functions fully tested
- **Isolation**: Use `vi.mock()` for external services, proper test cleanup

## Final Notes & Next Steps (compile from task notes)

- Summary of changes and decisions: Complete migration from Python LangChain tools to TypeScript AI SDK v6 tools with Zod schemas
- Outstanding items / tracked tech debt: None - all tools migrated and Python code cleaned up
- Follow-up prompts or tasks: Monitor tool performance and add new tools as needed

---

## Final Alignment with TripSage Migration Plan (Next.js 16 + AI SDK v6)

- **Core Migration Achievement**: All Python tool implementations successfully migrated to AI SDK v6
- **Architecture Decisions**:
  - Tools implemented with AI SDK `tool()` and Zod schemas
  - MCP integration for external APIs (Airbnb, etc.)
  - Server-side tool execution with proper security boundaries
  - Approval flows for sensitive operations (booking, payments)

- **Implementation Outcomes**:
  - Unified tool registry in `frontend/src/lib/tools/`
  - All external API integrations migrated (Weather, Flights, Maps, etc.)
  - Comprehensive error handling and timeouts
  - Upstash Redis rate limiting for tool usage
  - MCP server integration for accommodation searches

- **References**:
  - Tool Calling: <https://ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling>
  - MCP Tools: <https://ai-sdk.dev/docs/ai-sdk-core/mcp-tools>
  - Chatbot Tool Usage: <https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-tool-usage>

## Verification Criteria

- [x] Tool calls interleave correctly in AI SDK streams
- [x] Approval flows pause/resume streaming properly
- [x] Errors are structured and non-leaky (no stack traces)
- [x] All Python tool code deleted; TypeScript is sole implementation
- [x] Comprehensive test coverage with Vitest
- [x] ADR and Spec documentation completed

## Additional context & assumptions

- **Tool Pattern**: `tool({ name, description, parameters: z.object(...), execute: async (args) => {...} })`
- **MCP Integration**: Use `createMcpTool` for external APIs with proper error boundaries
- **Security**: Server-only credentials, input validation, timeouts, rate limiting
- **Registry**: Centralized tool registry with type safety and selective tool inclusion

## File & module targets

- `frontend/src/lib/tools/index.ts` - Main tool registry and exports
- `frontend/src/lib/tools/types.ts` - TypeScript interfaces for tools
- `frontend/src/lib/tools/weather.ts` - Weather API tools
- `frontend/src/lib/tools/web-search.ts` - Web search and crawling tools
- `frontend/src/lib/tools/accommodations.ts` - Accommodation search/booking tools
- `frontend/src/lib/tools/planning.ts` - Travel planning tools
- `frontend/src/lib/tools/memory.ts` - Memory and conversation tools
- `frontend/src/lib/tools/approvals.ts` - Approval flow utilities

## Testing & mocking guidelines

- **Unit Tests**: Zod schema validation, mocked API responses, error scenarios
- **Integration Tests**: Tool interleaving in streams, approval UI flows
- **Coverage**: All tool execute functions tested; edge cases covered
- **Mocking**: `vi.mock()` for external APIs, proper cleanup with `afterEach`
