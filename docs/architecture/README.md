# TripSage System Architecture

> **Target Audience**: Technical architects, senior developers, technical stakeholders, integration partners

This section contains high-level system design and architectural documentation for TripSage. Architecture documentation focuses on system design decisions, component interactions, and technology stack choices rather than implementation details.

## 📋 Documentation Scope

**✅ Architecture Documentation Includes:**

- System design patterns and architectural decisions
- Component interaction diagrams and data flow
- Technology stack choices and rationale
- Performance architecture and scalability patterns
- Security architecture and access patterns
- Integration architecture with external systems
- Cross-cutting concerns (caching, messaging, storage)

**❌ Architecture Documentation Excludes:**

- Implementation details and code examples → See [`docs/developers/`](../developers/)
- Deployment procedures and operations → See [`docs/operators/`](../operators/)
- API specifications and endpoints → See [`docs/api-reference/`](../api-reference/)
- Configuration and setup guides → See [`docs/configuration/`](../configuration/)

## 🏗️ Architecture Documents

### Core System Architecture

- **[System Overview](system-overview.md)** - Complete system architecture with component interactions, data flow, and technology stack
- **[Data Architecture](data-architecture.md)** - Database design patterns, storage decisions, and vector search optimization

### Specialized Architecture

- **[Storage Architecture](storage-architecture.md)** - File storage, bucket organization, and security patterns

## 🎯 Architecture Principles

TripSage follows these core architectural principles:

### 1. **Unified Data Architecture**

Single source of truth with Supabase PostgreSQL, eliminating complex multi-database patterns while supporting real-time features and vector operations.

### 2. **Consumer-Aware API Design**

API layer adapts responses and behavior based on consumer type (frontend applications vs AI agents), providing optimal experience for each use case.

### 3. **Performance-First Caching**

Serverless caching with Upstash Redis (HTTP), integrated via Vercel environment variables, eliminating local cache containers and connection pooling.

### 4. **Service Consolidation**

Direct SDK integrations replacing complex abstraction layers, reducing latency and improving maintainability while preserving functionality.

### 5. **Real-time Collaboration**

Supabase Realtime-based architecture enabling live trip planning, agent status updates, and multi-user collaboration with conflict resolution.

## 🏗️ Project Structure

```text
tripsage-ai/
├── tripsage/                   # API application (FastAPI)
├── tripsage_core/              # Core business logic and services
├── frontend/                   # Next.js application
├── tests/                      # Test suite (unit, integration, e2e, performance, security)
├── scripts/                    # Database and deployment scripts
├── docker/                     # Runtime compose files and Dockerfiles
├── docs/                       # Documentation
└── supabase/                   # Supabase configuration
```

### Module Organization

#### `tripsage/api/`

FastAPI application entry point and core API logic with consumer-aware design.

#### `tripsage_core/`

Core business logic, services, models, and shared utilities:

- `config.py` - Configuration management
- `exceptions.py` - Custom exception handling
- `models/` - Pydantic models and Supabase schemas
- `services/business/` - Business logic services
- `services/external_apis/` - Direct SDK integrations
- `services/infrastructure/` - Database, cache, Supabase Realtime integration

#### `frontend/`

Next.js 15 application with App Router and modern React patterns.

#### `tests/`

Comprehensive test suite with 90%+ coverage:

- `unit/` - Unit tests for individual components
- `integration/` - Service integration tests
- `e2e/` - End-to-end Playwright tests
- `performance/` - Performance and load tests
- `security/` - Security and compliance tests

## 🔗 Related Documentation

- **[Developers Guide](../developers/)** - Implementation details, code examples, testing
- **[API Documentation](../api/)** - REST specifications and Supabase Realtime guide
- **[Testing Guide](../../tests/README.md)** - Test organization and best practices
- **[Deployment](../operators/)** - Infrastructure, monitoring, and operations

## 📊 Architecture Metrics

Current production architecture achievements:

| Metric | Target | Achieved | Technology |
|--------|--------|----------|------------|
| Cache Performance | <10ms latency | **Edge/Global** | Upstash Redis |
| Concurrent Connections | 1000+ | **1500+** | Supabase Realtime |
| API Response Time | <100ms | **<50ms** | FastAPI |
| Database Connections | 500+ | **1000+** | Supabase PostgreSQL |
| Storage Cost Reduction | 50% | **80%** | Unified Architecture |

## 🚧 Architecture Evolution

### Current Phase: **Production Ready** (June 2025)

- ✅ Unified Supabase architecture implementation
- ✅ Upstash Redis serverless caching  
- ✅ Supabase Realtime communication
- ✅ Service consolidation and SDK migration
- ✅ Consumer-aware API design

### Next Phase: **Global Scale** (Q3-Q4 2025)

- 🔄 Multi-region deployment architecture
- 🔄 Monitoring and observability
- 🔄 Security and compliance patterns
- 🔄 Mobile application architecture

---

*For questions about system architecture or design decisions, please refer to the specific architecture documents or contact the technical architecture team.*
