# TripSage AI Frontend

## Core Capabilities

### AI & Intelligence Features

- **Multi-Provider Model Registry**: Centralized resolution supporting OpenAI, Anthropic, OpenRouter, xAI (Grok), and TogetherAI.
- **Hybrid RAG Pipeline**: Combines `pgvector` similarity search with **TogetherAI Reranking** (Mixedbread mxbai-rerank-large-v2) for ultra-accurate context retrieval.
- **Tool Approval Flow**: Sensitive operations (e.g., flight booking) require explicit user approval via a deterministic Redis-backed status tracker (`src/ai/tools/server/approvals.ts`).
- **Generative UI Framework**: Component-driven UI that streams rich interactive elements (Destination cards, Flight offers, Itinerary timelines) directly into the chat.
- **Token Budgeting**: Dynamic token counting and clamping using `js-tiktoken` to respect model context windows and optimize costs.
- **Memory & Checkpoints**: Conversation context management with LangGraph.js
  state persistence and Supabase storage.

### Security & Compliance

TripSage AI implements a military-grade security model designed for sensitive agentic operations:

- **BYOK (Bring Your Own Key)**: Users can provide their own API keys for AI providers, which are stored securely in **Supabase Vault** and never accessed by the application backend outside of resolution.
- **withApiGuards**: A unified factory for Next.js Route Handlers that centralizes:
  - **MFA (Multi-Factor Authentication)**: Enforces MFA sessions for sensitive tool operations.
  - **BotID Protection**: Blocks automated scraping and bot traffic using Vercel BotID (Kasada-powered).
  - **Rate Limiting**: Distributed rate limiting using Upstash Redis with sliding window logic.
  - **Bounded Payload Parsing**: Protects against DoS by enforcing strict request body size limits.
- **Proxy Pattern**: Uses a dedicated proxy (`src/proxy.ts`) for CSP nonce generation and applying baseline security headers (HSTS, CSP, etc.).
- **Token Budgeting**: Automatic counting (js-tiktoken), clamping, and
  usage tracking per provider to prevent overruns and control costs
- **Rate Limiting**: Centralized Upstash Redis sliding-window limits per
  user/IP with tiered budgets (40 req/min streaming, 20 req/min
  validation)
- **OpenTelemetry**: Distributed tracing with Trace Drains, span
  instrumentation, and PII redaction for observability without data
  leakage

### Performance & Scalability

- **Edge-First Architecture**: Next.js 16 proxy patterns, Vercel Edge
  runtime support, and Upstash Redis for sub-10ms global response times
- **Real-Time Collaboration**: Supabase Realtime private channels with Row
  Level Security for multi-user trip planning and agent status updates
- **React Compiler**: Automatic memoization and optimizations for
  zero-overhead reactive rendering
- **Streaming Everything**: SSE with `streamText`, tool calls interleaved
  in streams, and custom data streams for live UI updates
- **Attachment Handling**: File uploads to Supabase Storage with signed
  URLs, content validation, and rate-limited ingestion

## Core Tech Stack

The application leverages a modern, high-performance stack optimized for agentic workflows and real-time interactions:

- **Framework**: [Next.js 16](https://nextjs.org/) (App Router, Turbopack, React Compiler stable)
- **Library**: [React 19](https://react.dev/)
- **Intelligence**: [AI SDK v6](https://sdk.vercel.ai/docs) (with `ToolLoopAgent` and Multi-Provider Routing)
- **State Management**: [Zustand 5](https://github.com/pmndrs/zustand)
- **Database / Auth**: [Supabase](https://supabase.com/) (SSR, Realtime, Vault)
- **Middleware / Cache**: [Upstash Redis](https://upstash.com/) (Rate Limiting, Idempotency, Memory)
- **Styling**: Vanilla CSS (CSS Variables, Flex/Grid)
- **Observability**: [OpenTelemetry](https://opentelemetry.io/) (@vercel/otel)

## Code Quality & Patterns

This project follows strict DRY principles and established patterns:

- **API Routes**: Use `withApiGuards` factory
  ([guide](../core/development-guide.md#next-js-api-routes))
- **State Management**: Zustand with composition pattern
  ([guide](../standards/standards.md#zustand-stores))
- **Testing**: Centralized utilities in `src/test/`
  ([guide](../testing/testing.md))

## Feature Showcase

### Agentic Chat with Tool Calling

The chat interface automatically invokes relevant tools based on user
intent:

- **Travel Planning**: TypeScript-only tools in
  `src/lib/tools/planning.ts` (`createTravelPlan`,
  `updateTravelPlan`, `combineSearchResults`, `saveTravelPlan`,
  `deleteTravelPlan`)
- **Accommodations**: `search_accommodations` (via Airbnb),
  `get_accommodation_details`, `book_accommodation` (requires approval)
- **Flights**: `search_flights` (Duffel API), `book_flight` (requires
  approval)
- **Activities**: `search_activities` (Google Places API), `get_activity_details` (with optional AI/web fallback)
- **Calendar**: `createCalendarEvent` (Google Calendar), `getAvailability`
  (free/busy queries), `exportItineraryToICS` (ICS export)
- **Web Research**: `web_search` (Firecrawl v2.5, cached), `crawlUrl`
  (single-page scrape), `crawlSite` (multi-page crawl)
- **Weather**: `get_current_weather`, `get_forecast`,
  `get_travel_weather_summary`
- **Maps**: `get_directions`, `calculate_distance`, `geocode_location`
- **Memory**: `save_user_preferences`, `recall_conversation_context`,
  `search_memories`

All tools include Zod schema validation, timeouts, rate limiting, and
structured error handling.

#### Web Search (Firecrawl v2.5)

The `web_search` tool uses Firecrawl v2.5 API for web search with
advanced filtering and optional content scraping:

**Basic Usage:**

```typescript
webSearch.execute({
  query: "best restaurants in Paris",
  limit: 5,
  fresh: false, // Use cache if available
});
```

**Advanced Features:**

- **Sources**: Filter by result type (`web`, `news`, `images`)
- **Categories**: Search within specific domains (`github`, `research`,
  `pdf`)
- **Time Filters**: Use `tbs` parameter (`qdr:d` for past day, `qdr:w` for
  week, etc.)
- **Location**: Geographic filtering (e.g., `"Germany"`)
- **Content Scraping**: Optional `scrapeOptions` to fetch full page
  content

**Cost Optimization:**

- Search-only (no scraping): 2 credits per 10 results
- With scraping: Standard scraping costs apply
- **Cost-saving tips**:
  - Omit `scrapeOptions` unless you need full content
  - Set `parsers: []` in `scrapeOptions` to avoid PDF parsing costs (1
    credit/page)
  - Use `proxy: "basic"` instead of `"stealth"` unless required (+4
    credits per result)
  - Limit results with `limit` parameter (max 10)

**Example with all options:**

```typescript
webSearch.execute({
  query: "travel destinations 2025",
  limit: 8,
  sources: ["web", "news"],
  categories: ["research"],
  tbs: "qdr:m", // Past month
  location: "United States",
  timeoutMs: 30000,
  scrapeOptions: {
    formats: ["markdown"],
    parsers: [], // Avoid PDF costs
    proxy: "basic", // Cost-effective
  },
  fresh: false,
});
```

Results are cached in Redis for 1 hour (configurable via `fresh`
parameter).

#### Web Crawl/Scrape (Firecrawl v2.5)

The `crawlUrl` and `crawlSite` tools use Firecrawl v2.5 API for web
scraping and crawling:

**Single URL Scraping (`crawlUrl`):**

```typescript
crawlUrl.execute({
  url: "https://example.com",
  fresh: false,
  scrapeOptions: {
    formats: ["markdown", "html"],
    proxy: "basic",
  },
});
```

**Site Crawling (`crawlSite`):**

```typescript
crawlSite.execute({
  url: "https://docs.example.com",
  limit: 50,
  includePaths: ["/docs/*"],
  excludePaths: ["/admin/*"],
  sitemap: "include",
  scrapeOptions: {
    formats: ["markdown"],
    parsers: [], // Avoid PDF costs
    proxy: "basic",
  },
  pollInterval: 2, // seconds
  timeoutMs: 120000,
  maxPages: 5, // Early stop after 5 status checks
  fresh: false,
});
```

**Features:**

- **Formats**: `markdown`, `html`, `links`, `screenshot`, `summary`, or
  JSON mode with schema
- **Path Filtering**: `includePaths` and `excludePaths` for targeted
  crawling
- **Sitemap Control**: `sitemap: "include" | "skip" | "only"`
- **Client-Side Polling**: Automatic status polling with configurable
  intervals and limits
- **Cost Optimization**: Defaults avoid PDF parsing (`parsers: []`) and
  use basic proxy

**Cost Optimization:**

- Single scrape: Standard scraping costs (1 credit per page)
- Crawl: 1 credit per page scraped
- **Cost-saving tips**:
  - Set `parsers: []` to avoid PDF parsing costs (1 credit/page)
  - Use `proxy: "basic"` instead of `"stealth"` unless required (+4
    credits per page)
  - Use `maxPages` or `maxResults` to limit crawl size
  - Set `maxWaitTime` to prevent long-running crawls

Results are cached in Redis for 6 hours (configurable via `fresh`
parameter).

### Generative UI Streaming

Stream rich, interactive components directly into the chat using AI SDK v6:

```typescript
// Server: return data that triggers UI components in the ai-elements registry
return {
  type: "destination-card",
  data: {
    name: "Paris",
    rating: 4.8,
    photos: ["..."]
  }
};

// Client: Components in src/components/ai-elements automatically handle structured data
<MessageContent message={msg} />
// Handles <DestinationCard />, <FlightCard />, <ItineraryTimeline />, etc.
```

### Tool Approval Flow

Sensitive operations (e.g., booking a flight, modifying a calendar) pause streaming and require explicit user confirmation:

1. **Tool call detected**: The `bookAccommodation` tool requires approval.
2. **Approval Request**: The backend uses `requireApproval` (backed by Redis).
3. **UI Interaction**: The client receives an `approval_required` error code and displays a confirmation modal.
4. **Execution**: Once approved, the tool call is re-submitted with the same idempotency key.

## Development Scripts

### Operations CLI (`pnpm ops`)

TripSage AI uses a consolidated CLI for infrastructure, AI, and test operations:

```bash
pnpm ops infra check supabase  # Check Auth and Storage health
pnpm ops infra check upstash   # Test Redis and QStash connectivity
pnpm ops ai check config       # Validate AI provider setups (OpenRouter, OpenAI, etc.)
pnpm ops check all             # Full system health diagnostic
```

### Utility Scripts

| Script | Purpose |
| ------ | ------- |
| `pnpm ops` | Main entry point for local and production operations. |
| `vitest` | Modern, fast unit and integration testing suite. |
| `scripts/check-boundaries.mjs` | ESLint/Import-based check to prevent server-only code in client bundles. |
| `src/proxy.ts` | Development proxy for security headers and nonce generation. |

### Maintenance

No Git hooks required in the app. Repository-level hooks are managed via
pre-commit in the repo root.

## Environment configuration

The frontend uses a centralized environment variable system with explicit
server/client separation.

### Environment Architecture

Environment variables are managed through `src/lib/env/`:

- **`schema.ts`**: Shared Zod schemas for all environment variables
- **`server.ts`**: Server-only access (API routes, Server Components,
  server actions)
- **`client.ts`**: Client-safe access (only `NEXT_PUBLIC_*` variables)

### Key Rules

- **Server-only secrets**: Non-`NEXT_PUBLIC_` vars (e.g.
  `GOOGLE_MAPS_SERVER_API_KEY`, `FIRECRAWL_API_KEY`,
  `UPSTASH_REDIS_REST_TOKEN`, `AI_GATEWAY_API_KEY`) are read only in
  server routes/tools.
- **Client-side config**: Only `NEXT_PUBLIC_*` vars are exposed (e.g.
  `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
  `NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY`, `NEXT_PUBLIC_BASE_PATH`).
- **Supabase**: Production requires `NEXT_PUBLIC_SUPABASE_URL`,
  `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and `SUPABASE_JWT_SECRET`.
- **MFA backup codes**: Provide `MFA_BACKUP_CODE_PEPPER` (>=16 chars). If
  omitted, the app falls back to `SUPABASE_JWT_SECRET`, which must also be at
  least 16 characters to enable backup-code hashing.
- **AI/tools**: Configure provider keys as needed. Provider resolution
  follows this order: 1) User BYOK keys (from Supabase Vault), 2)
  Server-side fallback keys (`OPENAI_API_KEY`, `OPENROUTER_API_KEY`,
  `ANTHROPIC_API_KEY`, `XAI_API_KEY`), 3) Vercel AI Gateway
  (`AI_GATEWAY_API_KEY`). All provider keys are server-only.

### Usage Patterns

**Server-side** (API routes, Server Components, tools):

```typescript
import {
  getServerEnvVar,
  getServerEnvVarWithFallback,
  getGoogleMapsServerKey,
} from "@/lib/env/server";

const apiKey = getServerEnvVar("FIRECRAWL_API_KEY");
const mapsKey = getGoogleMapsServerKey();
const backendUrl = getServerEnvVarWithFallback(
  "BACKEND_API_URL",
  "http://localhost:8001",
);
```

**Client-side** (React components):

```typescript
import {
  getClientEnvVar,
  getClientEnvVarWithFallback,
  getGoogleMapsBrowserKey,
} from "@/lib/env/client";

const supabaseUrl = getClientEnvVar("NEXT_PUBLIC_SUPABASE_URL");
const mapsKey = getGoogleMapsBrowserKey(); // Returns undefined if not configured
const basePath = getClientEnvVarWithFallback("NEXT_PUBLIC_BASE_PATH", "");
```

**Never** use `process.env` directly in application code. Always use the
env helpers.

See `src/lib/env/schema.ts` for the full list of supported variables.

### HTTP Client (Unified)

All HTTP requests use a single, Zod-enabled client at
`src/lib/api/api-client.ts`.

- Import: `import { apiClient } from "@/lib/api/api-client"`.
- Base URL: `NEXT_PUBLIC_API_URL + "/api"` (falls back to `"/api"`).
- Endpoints: pass paths relative to this base (e.g., `"/trips"`, not
  `"/api/trips"`).
- Methods: `get`, `post`, `put`, `patch`, `delete`, plus helpers
  `sendChat` and `uploadAttachments`.
- Auth: use `useAuthenticatedApi()` which injects `Authorization` and
  calls `apiClient` internally.

### BYOK + Gateway

Resolution order per user:

1. Per-user Gateway key (service `gateway`) via `createGateway` from `ai`.
2. Per-provider BYOK: OpenAI, OpenRouter (via `createOpenAI` +
   baseURL=<https://openrouter.ai/api/v1>), Anthropic, xAI (via
   `@ai-sdk/xai`).
3. Team Gateway fallback (if configured) — consent-controlled.

Consent API:

- `GET /api/user-settings` → `{ allowGatewayFallback: boolean | null }`.
- `POST /api/user-settings` with `{ allowGatewayFallback: boolean }` to
  upsert owner row under RLS.

Server example with Gateway providerOptions (optional):

```typescript
import type { NextRequest } from "next/server";
import { resolveProvider } from "@ai/models/registry";
import { convertToModelMessages, streamText } from "ai";

export async function POST(req: NextRequest) {
  const { messages, model: modelHint } = await req.json();
  const userId = "user-ctx"; // from SSR auth
  const { model } = await resolveProvider(userId, modelHint);
  const result = await streamText({
    model,
    messages: convertToModelMessages(messages),
    providerOptions: {
      gateway: {
        order: ["anthropic", "openai"],
        budgetTokens: 200_000,
      },
    },
  });
  return result.toUIMessageStreamResponse();
}
```

- **Tracing**: OpenTelemetry spans track request flow across routes, providers, and tools (configured in `src/instrumentation.ts`).
- **Metrics**: Real-time tracking of token usage (`js-tiktoken`), latency, and error rates via `fireAndForgetMetric`.
- **Logs**: Structured JSON logging with PII redaction and secret masking (`redactErrorForLogging`).
- **Distributed tracing**: Spans `providers.resolve` include attributes `{ strategy: user-vault|server-fallback|gateway, provider, model }`.
