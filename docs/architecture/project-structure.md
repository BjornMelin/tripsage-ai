# Project Structure & Module Organization

This document provides the authoritative reference for the TripSage project structure and module organization.

## 🏗️ Overall Project Structure

```text
tripsage-ai/
├── tripsage/                   # API application
│   └── api/                    # FastAPI application
│       ├── __init__.py
│       └── main.py             # FastAPI application entry point
├── tripsage_core/              # Core business logic
│   ├── config.py               # Configuration management
│   ├── exceptions.py           # Custom exception handling
│   ├── models/                 # Pydantic models and schemas
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── schemas_common/
│   └── services/               # Business and infrastructure services
│       ├── __init__.py
│       ├── business/           # Business logic services (chat, API keys)
│       │   ├── __init__.py
│       │   ├── api_key_service.py
│       │   └── chat_service.py
│       └── infrastructure/     # Infrastructure services (cache, database)
│           ├── __init__.py
│           ├── cache_service.py
│           └── database_service.py
├── frontend/                   # Next.js application
│   ├── src/
│   │   ├── app/                # App Router pages and layouts
│   │   │   ├── __tests__/
│   │   │   ├── (auth)/
│   │   │   ├── (dashboard)/
│   │   │   ├── api/
│   │   │   ├── settings/
│   │   │   └── [other app files]
│   │   ├── components/         # Reusable React components
│   │   ├── contexts/           # React contexts
│   │   ├── hooks/              # Custom React hooks
│   │   ├── lib/                # Utilities and API clients
│   │   ├── middleware.ts
│   │   ├── schemas/            # Zod validation schemas
│   │   ├── stores/             # State management
│   │   ├── styles/
│   │   ├── test/
│   │   ├── test-setup.ts
│   │   ├── test-utils/
│   │   ├── types/              # TypeScript type definitions
│   │   └── __tests__/
│   └── [config files]
├── tests/                      # Comprehensive test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── database/
│   ├── docker/
│   ├── e2e/                    # End-to-end Playwright tests
│   ├── factories/              # Test data factories
│   ├── fixtures/               # Test data fixtures
│   ├── integration/            # Service integration tests
│   ├── performance/            # Performance tests
│   ├── security/               # Security tests
│   ├── unit/                   # Unit tests with 90%+ coverage
│   └── [config files]
├── scripts/                    # Database and deployment scripts
│   ├── automation/
│   ├── benchmarks/
│   ├── config/
│   ├── database/
│   ├── examples/
│   ├── maintenance/
│   ├── security/
│   ├── testing/
│   └── verification/
├── docker/                     # Runtime compose files and Dockerfiles
│   ├── dev_services/
│   ├── docker-compose.mcp.yml
│   ├── Dockerfile.api
│   └── [other config files]
├── docs/                       # Documentation
├── supabase/                   # Supabase configuration
├── legacy_tripsage/            # Legacy orchestration and agent code
├── legacy_tripsage_core/       # Legacy core business logic
└── [config files: pyproject.toml, uv.lock, etc.]
```

## 📁 Module Organization Guidelines

### tripsage/api/

Hosts the FastAPI application entry point and core API logic. Currently minimal with just API key management endpoints.

### tripsage_core/

Holds domain services, models, and shared exceptions—extend logic here, not in API layers.

- **config.py**: Configuration management
- **exceptions.py**: Custom exception handling
- **models/**: Pydantic models and schemas
- **services/business/**: Business logic services (chat, API keys)
- **services/infrastructure/**: Infrastructure services (cache, database)

### frontend/src/

Next.js 15 workspace with modern React patterns.

- **app/**: App Router pages and layouts
- **components/**: Reusable React components
- **lib/**: Utilities and API clients
- **hooks/**: Custom React hooks
- **contexts/**: React contexts
- **stores/**: State management
- **types/**: TypeScript type definitions
- **schemas/**: Zod validation schemas

### tests/

Comprehensive test suite split by type and scope.

- **unit/**: Unit tests with 90%+ coverage
- **integration/**: Service integration tests
- **e2e/**: End-to-end Playwright tests
- **performance/**: Performance tests
- **security/**: Security tests
- **fixtures/**: Test data fixtures
- **factories/**: Test data factories

### scripts/

Supporting automation for database tooling, security, testing, and deployment.

### docker/

Runtime compose files and Dockerfiles for containerized development and deployment.

## 🔄 Development Workflow

- **API Logic**: Extend `tripsage_core/` services, not API layers
- **UI Assets**: Keep under `frontend/public/`
- **Tests**: Maintain 90%+ backend coverage, 85%+ frontend coverage
- **Configuration**: Use `.env.example` as template, never commit secrets

## 📚 References

- [Repository Guidelines](../AGENTS.md) - Development and contribution guidelines
- [API Development Guide](../developers/api-development.md) - API-specific architecture and patterns
- [Testing Guide](../developers/testing-guide.md) - Testing structure and best practices
