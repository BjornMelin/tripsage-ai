# Developer Documentation

Resources and guidelines for TripSage development.

## Quick Reference

| Guide | Purpose |
|-------|---------|
| [Quick Start](quick-start.md) | Project setup, environment, first run |
| [Standards](standards.md) | TypeScript, import paths, Zod schemas, Zustand stores, security |
| [Development Guide](development-guide.md) | Architecture overview, key patterns, documentation index |
| [Testing](testing.md) | Strategy, patterns, templates, MSW handlers |
| [Troubleshooting](troubleshooting.md) | Debugging, CI/CD, workflow guidance |

## AI & Tools

| Guide | Purpose |
|-------|---------|
| [AI Integration](ai-integration.md) | Vercel AI Gateway, BYOK provider configuration |
| [AI Tools](ai-tools.md) | `createAiTool` factory, guardrails, tool patterns |
| [Activities](activities.md) | Activity search service, tools, API usage example |

## Infrastructure

| Guide | Purpose |
|-------|---------|
| [Zod Schema Guide](zod-schema-guide.md) | Zod v4 patterns, validation, AI SDK tool schemas |
| [Zustand Computed Middleware](zustand-computed-middleware.md) | Automatic computed properties for Zustand stores |
| [Observability](observability.md) | Telemetry spans, logging, operational alerts |
| [Cache Versioned Keys](cache-versioned-keys.md) | Tag-based cache invalidation patterns |
| [Environment Setup](env-setup.md) | Provider credential checklist |

## Development Workflow

```bash
# Install and run
cd frontend && pnpm install && pnpm dev

# Quality gates
cd frontend && pnpm biome:check && pnpm type-check && pnpm test:run
```

## Architecture

- **Framework**: Next.js 16 (TypeScript) — server route handlers + React Server Components
- **AI**: Vercel AI SDK v6 (`ai@6.0.0-beta.116`) with frontend-only agents
- **Database**: Supabase PostgreSQL with pgvector, RLS, Realtime
- **Cache**: Upstash Redis (HTTP REST API) + QStash for async jobs
- **State**: Zustand (client) + TanStack Query (server)

See [Development Guide](development-guide.md) for full-stack details and [Database Architecture](../architecture/database.md) for schema design.

## Finding Information

| Need | Go To |
|------|-------|
| New to the project | [Quick Start](quick-start.md) |
| Writing code | [Standards](standards.md) |
| Architecture overview | [Development Guide](development-guide.md) |
| Testing changes | [Testing](testing.md) |
| Having issues | [Troubleshooting](troubleshooting.md) |
| Database design | [Database Architecture](../architecture/database.md) |
