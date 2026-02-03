# Developer Documentation

Resources and guidelines for TripSage development.

## Quick Reference

| Guide | Purpose |
| ------- | --------- |
| [Quick Start](core/quick-start.md) | Project setup, environment, first run |
| [Standards](standards/standards.md) | TypeScript, import paths, Zod schemas, Zustand stores, security |
| [Layering Policy](architecture/layering.md) | Architecture layers, allowed dependencies, boundary enforcement |
| [Development Guide](core/development-guide.md) | Architecture overview, key patterns, documentation index |
| [Testing](testing/testing.md) | Strategy, patterns, templates, MSW handlers |
| [Troubleshooting](core/troubleshooting.md) | Debugging, CI/CD, workflow guidance |

## AI & Tools

| Guide | Purpose |
| ------- | --------- |
| [AI Integration](ai/ai-integration.md) | Vercel AI Gateway, BYOK provider configuration |
| [AI Tools](ai/ai-tools.md) | `createAiTool` factory, guardrails, tool patterns |
| [Activities](frontend/activities.md) | Activity search service, tools, API usage example |
| [Loading Components](frontend/loading-components.md) | Spinners, skeletons, wrappers, and loading hooks |

## Infrastructure

| Guide | Purpose |
| ------- | --------- |
| [Zod Schema Guide](standards/zod-schema-guide.md) | Zod v4 patterns, validation, AI SDK tool schemas |
| [Zustand Computed Middleware](frontend/zustand-computed-middleware.md) | Automatic computed properties for Zustand stores |
| [Observability](backend/observability.md) | Telemetry spans, logging, operational alerts |
| [Telemetry Data Classification](security/telemetry-data-classification.md) | Allowed/disallowed telemetry attributes and identifier policy |
| [Cache Versioned Keys](backend/cache-versioned-keys.md) | Tag-based cache invalidation patterns |
| [Environment Setup](core/env-setup.md) | Provider credential checklist |

## Development Workflow

```bash
# Install and run
pnpm install && pnpm dev

# Quality gates
pnpm biome:check && pnpm type-check && pnpm boundary:check && pnpm test

# Additional guardrails (run before merge)
pnpm ai-tools:check && pnpm check:fileoverviews && pnpm check:no-secrets && pnpm check:no-new-domain-infra-imports

# Repo-contract guardrails (recommended)
pnpm check:zod-v4:full && pnpm check:api-route-errors:full
```

## Architecture

- **Framework**: Next.js 16 (TypeScript) — server route handlers + React Server Components
- **AI**: Vercel AI SDK v6 (see [Stack Versions](../architecture/system-overview.md#stack-versions-source-of-truth-packagejson))
- **Database**: Supabase PostgreSQL with pgvector, RLS, Realtime
- **Cache**: Upstash Redis (HTTP REST API) + QStash for async jobs
- **State**: Zustand (client) + TanStack Query (server)

See [Development Guide](core/development-guide.md) for full-stack details and [Database Architecture](../architecture/database.md) for schema design.

## Finding Information

| Need | Go To |
| ------ | ------- |
| New to the project | [Quick Start](core/quick-start.md) |
| Writing code | [Standards](standards/standards.md) |
| Architecture overview | [Development Guide](core/development-guide.md) |
| Testing changes | [Testing](testing/testing.md) |
| Having issues | [Troubleshooting](core/troubleshooting.md) |
| Database design | [Database Architecture](../architecture/database.md) |
