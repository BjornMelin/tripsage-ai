# Developer Documentation

Resources and guidelines for TripSage development.

## Getting Started

| Guide | Purpose |
|-------|---------|
| [Quick Start](quick-start.md) | Project setup and development environment |
| [Code Standards](code-standards.md) | Coding guidelines and conventions |
| [Import Paths](import-paths.md) | TypeScript import path aliases and conventions |
| [Development Guide](development-guide.md) | API routes, state management, and patterns |
| [Stores](stores.md) | Zustand store patterns and composition |
| [Zod Schema Guide](zod-schema-guide.md) | Schema validation and type inference patterns |
| [Testing Guide](testing-guide.md) | Testing strategies and patterns |
| [Activities](activities.md) | Activity search service, tools, and API usage |

## Development

| Guide | Purpose |
|-------|---------|
| [Development Guide](development-guide.md) | Next.js backend/frontends, database patterns, and observability |
| [Observability](observability.md) | Telemetry spans, `[operational-alert]` contracts, and alerting guidance |
| [Troubleshooting](troubleshooting.md) | Debugging, CI/CD, and workflow guidance |

## Development Workflow

### Setup

```bash
# Install dependencies (frontend-first)
cd frontend && pnpm install

# Start development server (port 3000)
cd frontend && pnpm dev
```

### Code Quality

```bash
# TypeScript / Next.js
cd frontend && pnpm run biome:check && pnpm run type-check
cd frontend && pnpm test
```

## Architecture

- **Backend**: Next.js 16 server route handlers (TypeScript) — Python/FastAPI backend removed (see superseded SPEC-0007, SPEC-0010)
- **Frontend**: Next.js 16, TypeScript, Tailwind CSS
- **Database**: PostgreSQL (Supabase) with pgvector
- **Cache**: Upstash Redis (HTTP REST API)
- **AI**: Vercel AI SDK v6 with frontend-only agents

## Key Principles

- **Type Safety**: Strict TypeScript throughout
- **Async First**: All I/O operations use async/await
- **Security**: Environment variables only, JWT authentication
- **Testing**: Comprehensive test coverage required
- **Performance**: Efficient database queries and caching

## Finding Information

- **New to the project?** → [Quick Start](quick-start.md)
- **Writing code?** → [Code Standards](code-standards.md)
- **Building features?** → [Development Guide](development-guide.md)
- **Having issues?** → [Troubleshooting](troubleshooting.md)
