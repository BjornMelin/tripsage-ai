# Developer Documentation

Resources and guidelines for TripSage development.

## Getting Started

| Guide | Purpose |
|-------|---------|
| [Quick Start](quick-start.md) | Project setup and development environment |
| [Standards](standards.md) | Coding guidelines, import paths, schemas, stores |
| [Development Guide](development-guide.md) | API routes, state management, and patterns |
| [Testing](testing.md) | Strategy, patterns, and templates |
| [AI Integration](ai-integration.md) | Vercel AI SDK v6 and Gateway provider options |
| [AI Tools](ai-tools.md) | createAiTool factory, guardrails, and tool patterns |
| [Activities](activities.md) | Activity search service, tools, and API usage |
| [Environment Setup](env-setup.md) | Provider credential checklist |

## Development

| Guide | Purpose |
|-------|---------|
| [Development Guide](development-guide.md) | Next.js backend/frontends, database patterns, and observability |
| [Zod Schema Guide](zod-schema-guide.md) | Zod v4 schema patterns, validation, and AI SDK tool schemas |
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
- **Writing code?** → [Standards](standards.md)
- **Building features?** → [Development Guide](development-guide.md)
- **Testing changes?** → [Testing](testing.md)
- **Having issues?** → [Troubleshooting](troubleshooting.md)
