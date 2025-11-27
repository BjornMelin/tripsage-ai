# Quick Start

Get the TripSage development environment running quickly.

## Prerequisites

**Core Runtime:**

- Node.js ≥24 with pnpm ≥9.0.0
- Git

**External Services:**

- Supabase account (database and authentication)
- Upstash Redis (caching)
- OpenAI API key

**Optional:**

- Docker (for containerized development)
- PostgreSQL (alternative to Supabase)

**Tech Stack:**

- **Backend**: Next.js 16 server-first route handlers (TypeScript) — Python/FastAPI backend removed (see superseded SPEC-0007, SPEC-0010)
- **Frontend**: Next.js 16, React 19, TypeScript 5.9.3
- **Database**: PostgreSQL with pgvector (via Supabase)
- **Cache**: Upstash Redis (HTTP REST API)
- **AI**: Vercel AI SDK v6 with frontend-only agents (flights, accommodations, destinations, itineraries)
- **Auth**: Supabase JWT with middleware
- **Styling**: Tailwind CSS v4
- **State**: Zustand for client state
- **Data**: TanStack Query for server state
- **Testing**: Vitest 4.0.1, Playwright E2E
- **Linting**: Biome 2.2.7

## Setup

```bash
# Install Node.js package manager
npm install -g pnpm

# Clone and setup
git clone <repository-url>
cd tripsage-ai

# Install dependencies (frontend-only runtime)
cd frontend && pnpm install && cd ..

# Configure environment
cp .env.example .env
# Edit the root .env with your Supabase, Maps, and travel provider credentials
```

## Environment Variables

Required in `.env`:

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
DATABASE_SERVICE_KEY=your-service-key

# Optional: Redis for caching
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-token
```

## Start Development

```bash
# Frontend + API (Next.js, port 3000)
cd frontend && pnpm dev
```

## Verify

```bash
# Test frontend
open http://localhost:3000
```

## Development Workflow

### Code Quality

```bash
# Frontend: lint, format, type-check, test
cd frontend && pnpm biome:check && pnpm type-check
cd frontend && pnpm test
```

## Next Steps

- Read [Development Guide](development-guide.md) for technical details
- Check [Code Standards](code-standards.md) for guidelines
- Review [Testing Guide](testing-guide.md) for testing patterns
- See [Troubleshooting](troubleshooting.md) for debugging
