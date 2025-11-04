# TripSage AI Frontend

[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)](https://nextjs.org)
[![React](https://img.shields.io/badge/React-19-61dafb?logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178c6?logo=typescript)](https://typescriptlang.org)
[![AI SDK](https://img.shields.io/badge/AI_SDK-v6_beta-orange)](https://sdk.vercel.ai)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-v4-38bdf8?logo=tailwind-css)](https://tailwindcss.com)
[![Supabase](https://img.shields.io/badge/Supabase-SSR-3fcf8e?logo=supabase)](https://supabase.com)
[![Vitest](https://img.shields.io/badge/Vitest-✓-6e9f18?logo=vitest)](https://vitest.dev)
[![pnpm](https://img.shields.io/badge/pnpm-9+-f69220?logo=pnpm)](https://pnpm.io)

**Production-ready AI travel assistant with agentic tool calling, RAG-enhanced search, streaming intelligence, and enterprise-grade security.**

TripSage Frontend is a Next.js 16 application showcasing advanced AI SDK v6 integration patterns for production AI agents. It combines multi-provider LLM routing, agentic tool orchestration via MCP, hybrid RAG retrieval with reranking, and generative UI streaming—all with zero-trust security and server-side key management. From basic chat to multi-agent travel planning workflows with LangGraph.js state management, this frontend shows how to build autonomous agents for conversational AI applications.

## Core Capabilities

### AI & Intelligence

- **Multi-Provider Routing**: Automatic provider selection across OpenAI, Anthropic, xAI, and OpenRouter with fallback logic and attribution headers
- **Agentic Tool Calling**: 15+ production tools via AI SDK v6 with Zod schemas—web search, accommodations (MCP), flights (Duffel), weather, maps, planning, and memory
- **Hybrid RAG Pipeline**: Vector similarity (pgvector) + keyword search with provider-based reranking (Cohere Rerank v3.5) for optimal retrieval accuracy
- **Structured Outputs**: Schema-first LLM responses with `generateObject` for deterministic parsing and validation
- **Generative UI**: Component-driven responses that stream rich UI elements (itinerary cards, booking forms) beyond plain text
- **Memory & Checkpoints**: Conversation context management with LangGraph.js state persistence and Supabase storage

### Security & Compliance

- **BYOK Architecture**: User API keys encrypted in Supabase Vault, accessed only via SECURITY DEFINER RPCs with PostgREST JWT claims validation
- **Tool Approval Flows**: Sensitive operations (bookings, payments) pause streaming and require explicit user approval before execution
- **Token Budgeting**: Automatic counting (js-tiktoken), clamping, and usage tracking per provider to prevent overruns and control costs
- **Rate Limiting**: Centralized Upstash Redis sliding-window limits per user/IP with tiered budgets (40 req/min streaming, 20 req/min validation)
- **OpenTelemetry**: Distributed tracing with Trace Drains, span instrumentation, and PII redaction for observability without data leakage

### Performance & Scalability

- **Edge-First Architecture**: Next.js 16 proxy patterns, Vercel Edge runtime support, and Upstash Redis for sub-10ms global response times
- **Real-Time Collaboration**: Supabase Realtime private channels with Row Level Security for multi-user trip planning and agent status updates
- **React Compiler**: Automatic memoization and optimizations for zero-overhead reactive rendering
- **Streaming Everything**: SSE with `streamText`, tool calls interleaved in streams, and custom data streams for live UI updates
- **Attachment Handling**: File uploads to Supabase Storage with signed URLs, content validation, and rate-limited ingestion

### Developer Experience

- **AI SDK v6 Native**: Full migration from Python—TypeScript-first tools, unified provider API, and strict Zod validation
- **MCP Integration**: External APIs (Airbnb, weather, flights) bridged via Model Context Protocol for extensible tool ecosystems
- **Type-Safe Everything**: End-to-end TypeScript with strict mode, Zod schemas, and generated Supabase types
- **High Test Coverage**: 85-90% Vitest coverage with isolated unit tests, integration flows, and Playwright E2E scenarios
- **Modern Tooling**: Biome for zero-config linting/formatting, TanStack Query for data fetching, Zustand for state

## Tech Stack

- **Framework**: Next.js 16 with React 19 and App Router
- **AI SDK**: AI SDK v6 (core + React hooks + UI Elements)
- **Providers**: OpenAI, Anthropic, xAI, OpenRouter (BYOK multi-provider)
- **Language**: TypeScript 5.9 with strict mode
- **Styling**: Tailwind CSS v4 with CSS-first config
- **Data/Auth**: Supabase SSR auth with pgvector for embeddings
- **Ratelimit & Cache**: Upstash Redis for distributed rate limiting and caching
- **Types & Schemas**: Zod v3 for runtime validation
- **UI Components**: Radix UI primitives with Tailwind styling
- **State Management**: Zustand for client state
- **Data Fetching**: TanStack Query v5 for server state
- **Testing**: Vitest (unit + integration) + Playwright (e2e)
- **Code Quality**: Biome (single gate for linting/formatting)
- **Observability**: OpenTelemetry with Trace Drains
- **Package Manager**: pnpm ≥9.0.0
- **Runtime**: Node.js ≥24

## Quick Start

```bash
pnpm install  # Install dependencies
pnpm dev      # Start development server
```

Open [http://localhost:3000](http://localhost:3000) to view the app.

## Feature Showcase

### Agentic Chat with Tool Calling

The chat interface automatically invokes relevant tools based on user intent:

- **Travel Planning**: `create_travel_plan`, `update_travel_plan`, `generate_travel_summary`
- **Accommodations**: `search_accommodations` (via Airbnb MCP), `get_accommodation_details`, `book_accommodation` (requires approval)
- **Flights**: `search_flights` (Duffel API), `book_flight` (requires approval)
- **Web Research**: `web_search` (cached), `crawl_website`, `crawl_travel_blog`
- **Weather**: `get_current_weather`, `get_forecast`, `get_travel_weather_summary`
- **Maps**: `get_directions`, `calculate_distance`, `geocode_location`
- **Memory**: `save_user_preferences`, `recall_conversation_context`, `search_memories`

All tools include Zod schema validation, timeouts, rate limiting, and structured error handling.

### RAG-Enhanced Responses

Hybrid retrieval combines vector similarity and keyword search for optimal accuracy:

1. **Embedding**: Provider-based embeddings (OpenAI, Cohere) stored in Supabase pgvector
2. **Retrieval**: Hybrid query returns top-k candidates (vector + keyword fusion)
3. **Reranking**: Cohere Rerank v3.5 refines results for relevance
4. **Caching**: Upstash Redis caches hot queries with short TTL
5. **Indexing**: CLI and API routes for document ingestion with chunking

### Generative UI Streaming

Stream rich, interactive components beyond text:

```typescript
// Server: Emit generative UI parts
streamData({
  type: 'itinerary-card',
  data: { destinations: [...], activities: [...] }
});

// Client: Render component blocks
<GenerativeMessage message={msg}>
  {msg.content.type === 'itinerary-card' && <ItineraryCard {...msg.content.data} />}
</GenerativeMessage>
```

### Tool Approval Flow

Sensitive operations pause streaming and request user confirmation:

1. Tool call detected (e.g., `book_accommodation`)
2. Stream pauses, approval modal appears
3. User approves/denies with context preview
4. Stream resumes with tool execution or cancellation

## Development Scripts

### Core Commands

```bash
pnpm dev          # Start development server
pnpm build        # Production build
pnpm build:analyze # Build with bundle analyzer
pnpm start        # Start production server
```

### Code Quality

```bash
pnpm lint         # Lint code with Biome
pnpm biome:check  # Lint and format check
pnpm biome:fix    # Auto-fix linting issues
pnpm format:biome # Format code with Biome
pnpm type-check   # TypeScript type checking
```

### Testing

```bash
pnpm test         # Run tests (watch mode)
pnpm test:run     # Run tests once
pnpm test:short   # Run tests with short timeouts
pnpm test:ui      # Run tests with UI
pnpm test:coverage # Run tests with coverage
pnpm test:e2e     # Run E2E tests
```

### Maintenance

No Git hooks setup is required in the frontend. Repository-level hooks are managed via pre-commit in the repo root.

### Code Mods (AI SDK v6 migration)

```bash
pnpm codemod:ai-route:dry     # Dry run: Update AI routes
pnpm codemod:ai-route         # Update AI routes
pnpm codemod:ai-messages:dry  # Dry run: Convert AI messages
pnpm codemod:ai-messages      # Convert AI messages
pnpm codemod:tests-env:dry    # Dry run: Update test env stubs
pnpm codemod:tests-env        # Update test env stubs
pnpm codemod:validate         # Validate codemod changes
pnpm codemod:check-idempotency # Check codemod idempotency
```

## Project Structure

```text
frontend/
├── src/
│   ├── app/               # Next.js App Router
│   │   ├── (auth)/        # Authentication routes
│   │   ├── (dashboard)/   # Protected dashboard routes
│   │   ├── api/           # API routes & handlers
│   │   │   ├── chat/      # Chat API (streaming + non-streaming)
│   │   │   ├── keys/      # BYOK management routes
│   │   │   ├── rag/       # RAG indexing routes
│   │   │   └── tools/     # Tool execution endpoints
│   │   ├── auth/          # Auth callbacks
│   │   ├── chat/          # Chat interface with AI Elements
│   │   └── settings/      # User settings & API key management
│   ├── components/        # React components
│   │   ├── ui/            # Reusable UI primitives (Radix + Tailwind)
│   │   ├── features/      # Feature-specific components
│   │   ├── layouts/       # Layout components
│   │   ├── providers/     # React context providers
│   │   ├── ai-elements/   # AI chat components (conversation, message, prompt)
│   │   ├── generative/    # Generative UI components (cards, forms)
│   │   └── error/         # Error boundaries
│   ├── lib/               # Core utilities
│   │   ├── api/           # API clients
│   │   ├── supabase/      # Database integration + RPC helpers
│   │   ├── providers/     # AI provider registry & resolution
│   │   ├── tools/         # Tool registry with Zod schemas
│   │   │   ├── index.ts   # Unified tool exports
│   │   │   ├── web.ts     # Web search and crawling
│   │   │   ├── accommodations.ts # Accommodation tools + MCP
│   │   │   ├── flights.ts # Flight search (Duffel)
│   │   │   ├── weather.ts # Weather API tools
│   │   │   ├── maps.ts    # Google Maps integration
│   │   │   ├── planning.ts # Travel planning tools
│   │   │   └── memory.ts  # Memory and conversation tools
│   │   ├── rag/           # RAG retriever + indexer
│   │   ├── schemas/       # Zod validation schemas
│   │   ├── repositories/  # Data access layer
│   │   ├── tokens/        # Token counting + budgeting
│   │   └── telemetry/     # OpenTelemetry instrumentation
│   ├── hooks/             # Custom React hooks
│   ├── stores/            # Zustand state stores
│   ├── types/             # TypeScript definitions
│   ├── styles/            # Global styles & CSS
│   ├── __tests__/         # Unit tests
│   └── test-utils/        # Testing utilities
├── docs/                  # Documentation
├── scripts/               # Build & utility scripts
├── e2e/                   # End-to-end tests
├── public/                # Static assets
├── coverage/              # Test coverage reports
├── test-results/          # Test artifacts
└── *.config.*             # Configuration files
    ├── package.json       # Dependencies & scripts
    ├── biome.json         # Code formatting/linting
    ├── tsconfig.json      # TypeScript configuration
    ├── next.config.ts     # Next.js configuration
    ├── vitest.config.ts   # Testing configuration
    └── playwright.config.ts # E2E testing
```

## Environment Variables

Create a `.env.local` file:

```bash
# Supabase (Required)
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key  # Server-only

# Rate Limiting & Caching (Required)
UPSTASH_REDIS_REST_URL=your_upstash_rest_url
UPSTASH_REDIS_REST_TOKEN=your_upstash_rest_token

# AI Gateway (Optional - for provider routing)
AI_GATEWAY_URL=your_vercel_ai_gateway_url

# External APIs (Optional - for tool functionality)
OPENWEATHER_API_KEY=your_openweather_key
DUFFEL_ACCESS_TOKEN=your_duffel_token
GOOGLE_MAPS_API_KEY=your_google_maps_key

# MCP Servers (Optional - for extended tool ecosystem)
AIRBNB_MCP_URL=your_airbnb_mcp_endpoint

# Observability (Optional)
OTEL_EXPORTER_OTLP_ENDPOINT=your_otel_collector
```

## Architecture Highlights

### AI SDK v6 Migration

This frontend represents a complete migration from Python-based LangChain tools to AI SDK v6 TypeScript implementation:

- **Before**: Python FastAPI routes with LangChain agents, custom streaming, mixed provider wrappers
- **After**: Next.js routes with AI SDK v6 `streamText`, Zod tools, unified provider registry
- **Benefits**: 50% less code, type-safe tools, native streaming, simplified testing, edge runtime support

### Security Model

Zero-trust architecture with defense-in-depth:

1. **BYOK**: User keys never touch client; encrypted at rest in Supabase Vault
2. **RLS**: Row Level Security enforces data isolation per user
3. **Claims Validation**: PostgREST JWT claims guard all RPC calls
4. **Rate Limiting**: Upstash Redis enforces sliding-window limits per user/IP
5. **PII Redaction**: OpenTelemetry spans automatically redact sensitive data
6. **Approval Gates**: Critical operations require explicit user consent

### Observability

Full-stack instrumentation without compromising privacy:

- **Tracing**: OpenTelemetry spans track request flow across routes, providers, tools
- **Metrics**: Token usage, latency, error rates, cache hit ratios
- **Logs**: Structured logging with correlation IDs and PII redaction
- **Drains**: Trace data exported to OTEL collector for analysis

## Further Reading

### Development

- [Frontend Development Guide](../docs/developers/frontend-development.md) - Frontend architecture & patterns
- [Testing Guide](../docs/developers/testing-guide.md) - Testing strategies & coverage requirements
- [Code Standards](../docs/developers/code-standards.md) - Code quality & conventions
- [AI SDK Migration Prompts](../docs/prompts/ai-sdk/RUN-ORDER.md) - Complete migration guide

### API Integration

- [API Reference](../docs/api/api-reference.md) - REST API documentation
- [Realtime API](../docs/api/realtime-api.md) - Supabase realtime integration
- [Error Codes](../docs/api/error-codes.md) - API error handling reference

### Architecture

- [System Overview](../docs/architecture/README.md) - High-level architecture
- [Data Architecture](../docs/architecture/data-architecture.md) - Database & data flow design
- [Storage Architecture](../docs/architecture/storage-architecture.md) - File storage & caching

### Operations

- [Deployment Guide](../docs/operators/deployment-guide.md) - Production deployment
- [Security Guide](../docs/operators/security-guide.md) - Security implementation
- [Operators Reference](../docs/operators/operators-reference.md) - DevOps operations

### Decision Records

- [Architecture Decisions](../docs/adrs/README.md) - Technical decision history
- [AI SDK v6 ADRs](../docs/adrs/adr-0023-adopt-ai-sdk-v6-foundations.md) - AI SDK migration decisions
- [Technical Debt](../docs/TECH_DEBT.md) - Known technical debt & priorities

## Key Architectural Decisions

This frontend embodies several critical architectural decisions:

- **[ADR-0023](../docs/adrs/adr-0023-adopt-ai-sdk-v6-foundations.md)**: AI SDK v6 foundations with streaming and server-only secrets
- **[ADR-0024](../docs/adrs/adr-0024-byok-routes-and-security.md)**: BYOK architecture with Supabase Vault
- **[ADR-0026](../docs/adrs/adr-0026-adopt-ai-elements-ui-chat.md)**: AI Elements for standardized chat UI
- **[ADR-0028](../docs/adrs/adr-0028-provider-registry.md)**: Multi-provider registry with fallback and attribution
- **[ADR-0031](../docs/adrs/adr-0031-nextjs-chat-api-ai-sdk-v6.md)**: Next.js chat API with SSE and non-stream modes
- **[ADR-0033](../docs/adrs/adr-0033-rag-advanced-v6.md)**: Hybrid RAG with reranking
- **[ADR-0034](../docs/adrs/adr-0034-structured-outputs-object-generation.md)**: Structured outputs with `generateObject`

## Conventions

- Node version is sourced from the repo root `/.nvmrc` (`v24`).
- Tailwind CSS v4 uses PostCSS plugin; a minimal `tailwind.config.mjs` exists to satisfy shadcn tooling.
- All linting/formatting via Biome; do not add ESLint/Prettier. Fix code rather than relaxing rules.
- Ignore rules are centralized in the repo root `.gitignore`.
- Local quality gates:
  - `pnpm biome:check && pnpm type-check && pnpm test:run`
  - Optional UI: `pnpm test:ui`

## Contributing

See the [Developer Contributing Guide](../docs/developers/contributing.md) for code standards, testing requirements, and PR workflow.

## License

MIT - See [LICENSE](../LICENSE) for details.

---

**Built by Bjorn Melin** as an exploration of production AI application patterns with Next.js, AI SDK v6, modern TypeScript, and Vercel.
