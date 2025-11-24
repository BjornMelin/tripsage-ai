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
  [`docs/developers/`](../developers/)
- Deployment procedures and operations → See
  [`docs/operators/`](../operators/)
- API specifications and endpoints → See
  [`docs/api-reference/`](../api-reference/)
- Configuration and setup guides → See
  [`docs/configuration/`](../configuration/)

## Architecture Documents

### Core System Architecture

- **[System Overview](system-overview.md)** - Complete system architecture
  with component interactions, data flow, and technology stack
- **[Frontend Architecture](frontend-architecture.md)** - Next.js
  application structure, AI SDK v6 integration, component organization,
  and data flows

### Database & Storage Architecture

- **[Database Architecture](database/)** - Supabase PostgreSQL design, schema patterns, and data models
  - **[Supabase Schema](database/supabase-schema.md)** - Canonical database schema and migration strategy
  - **[Supabase Integration](database/supabase-integration.md)** - Authentication, SSR patterns, and client configurations
  - **[Supabase Operations](database/supabase-operations.md)** - Webhooks, real-time features, and operational patterns
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
├── frontend/                   # Next.js 16 app (server-first routes + UI)
├── docs/                       # Documentation (specs, ADRs, guides)
├── docker/                     # Runtime compose files and Dockerfiles
├── scripts/                    # Database and deployment scripts
├── supabase/                   # Supabase configuration
└── worktrees/                  # Auxiliary git worktrees (if used)
```

### Module Organization

#### `frontend/`

Next.js 16 application with App Router and React 19. See
[Frontend Architecture](frontend-architecture.md) for detailed
structure, AI SDK v6 integration, and component organization.

#### `tests/`

Test suite with 90%+ coverage:

- `unit/` - Unit tests for individual components
- `integration/` - Service integration tests
- `e2e/` - End-to-end Playwright tests
- `performance/` - Performance and load tests
- `security/` - Security and compliance tests

## Related Documentation

- **[Database Operations](../operators/database/)** - Database operations and Supabase configuration
- **[Developers Guide](../developers/)** - Implementation details, code
  examples, testing
- **[API Documentation](../api/)** - REST specifications and Supabase
  Realtime guide
- **[Testing Guide](../../tests/README.md)** - Test organization and best
  practices
- **[Deployment](../operators/)** - Infrastructure, monitoring, and
  operations

## Architecture Metrics

Current architecture metrics:

| Metric | Target | Achieved | Technology |
|--------|--------|----------|------------|
| Cache Performance | <10ms latency | **Edge/Global** | Upstash Redis |
| Concurrent Connections | 1000+ | **1500+** | Supabase Realtime |
| API Response Time | <100ms | **<50ms** | FastAPI |
| Database Connections | 500+ | **1000+** | Supabase PostgreSQL |
| Storage Cost Reduction | 50% | **80%** | Unified Architecture |

## Architecture Evolution

### Current Phase (June 2025)

- Unified Supabase architecture implementation
- Upstash Redis serverless caching  
- Supabase Realtime communication
- Service consolidation and SDK migration
- Consumer-aware API design

### Next Phase (Q3-Q4 2025)

- Multi-region deployment architecture
- Monitoring and observability
- Security and compliance patterns
- Mobile application architecture

---

*For questions about system architecture or design decisions, refer to
the specific architecture documents or contact the technical
architecture team.*
