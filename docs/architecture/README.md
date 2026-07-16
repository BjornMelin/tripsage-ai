# TripSage System Architecture

> **Target Audience**: Technical architects, senior developers, technical
> stakeholders, integration partners

This section contains high-level system design and architectural
documentation for TripSage. The focus is on system design decisions,
component interactions, and technology stack choices rather than
implementation details.

## Documentation Scope

**Architecture Documentation Includes:**

- System design patterns and architectural decisions
- Component interaction diagrams and data flow
- Technology stack choices and rationale
- Performance architecture and scalability patterns
- Security architecture and access patterns
- Integration architecture with external systems
- Cross-cutting concerns (caching, messaging, storage)

**Architecture Documentation Excludes:**

- Implementation details and code examples → See
  [`docs/development/`](../development/)
- Deployment procedures and operations → See
  [`docs/operations/`](../operations/)
- API specifications and endpoints → See
  [`docs/api/`](../api/)
- Configuration and setup guides → See
  [Development Guide](../development/core/development-guide.md)

## Architecture Documents

### Core System Architecture

- **[System Overview](system-overview.md)** - Complete system architecture
  with component interactions, data flow, and technology stack
- **[Frontend Architecture](frontend-architecture.md)** - Next.js
  application structure, AI SDK v7 integration, component organization,
  and data flows

### Database & Storage Architecture

- **[Database Architecture](database.md)** - Supabase PostgreSQL, Auth, Vault, Realtime, and migration strategy
- **[Storage Architecture](storage-architecture.md)** - File storage,
  bucket organization, and security patterns

### Specialized Architecture

- **[Route Exceptions](route-exceptions.md)** - Exception criteria for API
  factory bypass

## Architecture Principles

TripSage follows these core architectural principles:

### 1. **Unified Data Architecture**

Single source of truth with Supabase PostgreSQL, eliminating complex
multi-database patterns while supporting real-time features and vector
operations.

### 2. **Consumer-Aware API Design**

API layer adapts responses and behavior based on consumer type (frontend
applications vs AI agents).

### 3. **Serverless Caching**

Serverless caching with Upstash Redis (HTTP), integrated via Vercel
environment variables, eliminating local cache containers and connection
pooling.

### 4. **Service Consolidation**

Direct SDK integrations replace complex abstraction layers, reducing
latency and improving maintainability while preserving functionality.

### 5. **Real-time Collaboration**

Supabase Realtime-based architecture for live trip planning, agent
status updates, and multi-user collaboration.

## Project Structure

```text
tripsage-ai/
├── src/                        # Next.js 16 app source (App Router, components, libs)
├── docs/                       # Documentation (specs, ADRs, guides)
├── docker/                     # Runtime compose files and Dockerfiles
├── scripts/                    # Database and deployment scripts
├── supabase/                   # Supabase configuration
└── worktrees/                  # Auxiliary git worktrees (if used)
```

### Module Organization

#### `src/`

Next.js 16 application with App Router and React 19. See
[Frontend Architecture](frontend-architecture.md) for detailed
structure, AI SDK v7 integration, and component organization.

#### Tests

Tests live next to the code they exercise under `src/**/__tests__` plus
Playwright specs in `e2e/`. See
[Testing Guide](../development/testing/testing.md) for the current Vitest,
Playwright, critical-flow, and live-smoke lanes.

## Related Documentation

- **[Database Operations](../operations/runbooks/database-ops.md)** - Database operations and Supabase configuration
- **[Development Guide](../development/core/development-guide.md)** - Implementation details, code
  examples, testing
- **[API Documentation](../api/)** - REST specifications and Supabase
  Realtime guide
- **[Testing Guide](../development/testing/testing.md)** - Test organization and best
  practices
- **[Deployment](../operations/)** - Infrastructure, monitoring, and
  operations

## Current Baseline

- Next.js 16 + React 19 application at repository root.
- Supabase SSR/Auth/Vault/Realtime and pgvector as the data plane.
- Upstash Redis/QStash/Ratelimit as the cache, rate-limit, and job plane.
- AI SDK v7 with Provider V4 Vercel AI Gateway and BYOK resolution.
- Vercel CLI prebuilt deploys with smoke-before-promote.

---

_For questions about system architecture or design decisions, refer to
the specific architecture documents or contact the technical
architecture team._
