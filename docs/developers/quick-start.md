# Quick Start

Get the TripSage development environment running quickly.

## Prerequisites

**Core Runtime:**

- Python 3.13+ with uv package manager
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

- **Backend**: FastAPI with async Python
- **Frontend**: Next.js 16, React 19, TypeScript 5.9.3
- **Database**: PostgreSQL with pgvector (via Supabase)
- **Cache**: Upstash Redis (HTTP REST API)
- **AI**: OpenAI GPT-4/GPT-5, LangGraph orchestration, Mem0 memory
- **Auth**: Supabase JWT with middleware
- **Styling**: Tailwind CSS v4
- **State**: Zustand for client state
- **Data**: TanStack Query for server state
- **Testing**: Vitest 4.0.1, Playwright E2E
- **Linting**: Biome 2.2.7, Ruff for Python

## Setup

```bash
# Install Python package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Node.js package manager
npm install -g pnpm

# Clone and setup
git clone <repository-url>
cd tripsage-ai

# Install dependencies
uv sync
cd frontend && pnpm install && cd ..

# Configure environment
cp .env.example .env
# Edit .env with your Supabase credentials
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
# Backend API (port 8000)
uv run python -m tripsage.api.main

# Frontend (port 3000, separate terminal)
cd frontend && pnpm dev
```

## Verify

```bash
# Test API health
curl http://localhost:8000/health

# Test frontend
open http://localhost:3000
```

## Development Workflow

### Code Quality

```bash
# Python: lint and format
ruff check . --fix && ruff format .

# Python: test
uv run pytest --cov=tripsage

# Frontend: lint and format
cd frontend && pnpm lint && pnpm format

# Frontend: test
cd frontend && pnpm test
```

## Next Steps

- Read [Development Guide](development-guide.md) for technical details
- Check [Code Standards](code-standards.md) for guidelines
- Review [Testing Guide](testing-guide.md) for testing patterns
- See [Troubleshooting](troubleshooting.md) for debugging
