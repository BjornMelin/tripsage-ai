# Quick Start Guide

Get the TripSage development environment running in 15 minutes.

## Prerequisites

- Python 3.12+
- Node.js 24+
- Next.js 16+
- pnpm 9+
- Tailwind CSS 4+
- TypeScript 5+
- React 19+
- Zustand 5+
- TanStack Query 5+
- React Hook Form 7+
- Biome 2+
- Git
- Docker
- Supabase 2.22.0+
- Upstash 1.4.0+
- Redis 6.4.0+
- PostgreSQL 16.4+
- pgvector 0.5.0+
- Mem0 0.1.118+

## Install Tools

```bash
# Python package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Node.js package manager
npm install -g pnpm
```

## Project Setup

```bash
# Clone repository
git clone <repository-url>
cd tripsage-ai

# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend && pnpm install && cd ..

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

## Environment Variables

Required in `.env`:

```bash
# Backend (FastAPI)
NEXT_PUBLIC_API_URL=http://localhost:8001

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# Optional: Upstash Redis (enables Next.js route rate limits)
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-token
```

## Start Development

```bash
# API server (port 8000)
uv run python -m tripsage.api.main

# Frontend (port 3000, separate terminal)
cd frontend && pnpm dev
```

## Verify Setup

```bash
# Test API
curl http://localhost:8000/api/health

# Test frontend
open http://localhost:3000

## Feature Check

- Streaming chat: open the chat UI, send a prompt; the assistant message should update progressively (SSE via `/api/chat/stream`).
- Attachments SSR listing: after uploading, the attachments list route (`/api/attachments/files`) is revalidated by `revalidateTag('attachments','max')`.
```

## Development Workflow

### Code Changes

```bash
# Python linting and formatting
ruff check . --fix && ruff format .

# TypeScript linting and formatting
cd frontend && pnpm lint && pnpm format
```

### Testing

```bash
# Backend tests
uv run pytest --cov=tripsage

# Frontend tests
cd frontend && pnpm test
```

## Next Steps

- Read [Code Standards](code-standards.md) for development guidelines
- Check [Backend Development](backend-development.md) for API work
- Review [Testing Guide](testing-guide.md) for testing patterns
- See [Branch Conventions](branch-conventions.md) for Git workflow
