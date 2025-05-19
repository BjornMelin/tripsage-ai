# TripSage Frontend Technology Stack Summary

## Definitive Frontend Technology Stack

### Core Technologies

- **Framework**: Next.js 15.3 with App Router and Turbopack
- **UI Library**: React 19 with concurrent features
- **Language**: TypeScript 5.5 with strict mode
- **Styling**: Tailwind CSS v4 (OKLCH colors) + shadcn/ui v3-canary
- **State Management**: Zustand v5 (client) + TanStack Query v5 (server)
- **Forms**: React Hook Form v8 + Zod v3
- **AI/Streaming**: Vercel AI SDK v5 with SSE
- **Authentication**: Supabase Auth (existing backend integration)
- **Maps**: Mapbox GL JS v3
- **Visualization**: React Flow v12 + Recharts v2
- **Testing**: Vitest v2 + Playwright v1.48+
- **Deployment**: Vercel with edge runtime

## Key Architecture Decisions

### 1. Authentication Strategy

**Decision**: Supabase Auth

- **Justification**:
  - Already integrated with the FastAPI backend
  - Provides JWT tokens compatible with existing backend
  - Includes built-in user management and session handling
  - Supports social login and magic links
- **Implementation**: Server-side auth with cookies and middleware protection

### 2. Real-time Communication

**Decision**: Server-Sent Events (SSE) via Vercel AI SDK v5

- **Justification**:
  - Ideal for unidirectional streaming (server → client)
  - Built-in browser support with automatic reconnection
  - Firewall-friendly (uses standard HTTP)
  - Perfect for AI agent response streaming
- **Fallback**: WebSocket for bidirectional needs

### 3. API Key Management

**Decision**: Backend Proxy Pattern

- **Justification**:
  - Never expose sensitive keys to the client
  - All MCP tool invocations go through FastAPI backend
  - User API keys stored encrypted in backend database
  - Frontend only holds JWT tokens for authentication
- **Implementation**: Next.js API routes proxy to FastAPI

### 4. Technology Versions

All selected versions are SOTA as of January 2025:

- Next.js 15.3: Latest with Turbopack production support
- React 19: Stable release with new hooks (use, useOptimistic)
- TypeScript 5.5: Latest with enhanced type inference
- Tailwind CSS v4: Alpha with OKLCH color space
- Vercel AI SDK v5: New UI Message Streaming Protocol

## Integration Strategy

### Backend Communication

```typescript
// Frontend → FastAPI → MCP Servers
const response = await fetch('/api/mcp/flights/search', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ origin: 'NYC', destination: 'LON' })
})
```

### Agent Streaming

```typescript
// SSE streaming from FastAPI backend
const { messages, input, handleSubmit } = useChat({
  api: '/api/agents/travel-planner/stream',
  streamProtocol: 'data-stream',
  onFinish: (message) => {
    // Handle completed response
  }
})
```

### Authentication Flow

```typescript
// Supabase Auth with server-side session
const supabase = createServerClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  { cookies }
)
```

## Performance Optimizations

- **Turbopack**: 28-83% faster builds than Webpack
- **React 19**: Automatic batching and concurrent features
- **Server Components**: Reduced client bundle size
- **Streaming UI**: Progressive rendering for better UX
- **Code Splitting**: Dynamic imports for heavy components
- **Image Optimization**: Next.js built-in image optimization

## Security Considerations

- **Backend Proxy**: All sensitive operations through FastAPI
- **JWT Validation**: Server-side token verification
- **CSP Headers**: Strict content security policy
- **Input Validation**: Zod schemas for all user input
- **Session Management**: Secure cookies with httpOnly flag

## Development Workflow

1. **Linting**: Biome (JS/TS equivalent of ruff)
2. **Testing**: Vitest for unit, Playwright for E2E
3. **Type Checking**: TypeScript strict mode
4. **Pre-commit**: Husky hooks for quality checks
5. **CI/CD**: GitHub Actions → Vercel deployment

## Success Metrics

- Lighthouse score > 95
- Page load time < 1.5s
- Test coverage > 80%
- TypeScript strict compliance
- Zero security vulnerabilities

This technology stack ensures:

- Excellent developer experience
- High performance and scalability
- Strong type safety throughout
- Modern AI capabilities
- Seamless backend integration
- Production-ready from day one
