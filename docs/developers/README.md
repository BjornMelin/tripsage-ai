# TripSage Developer Documentation

Internal developer resources and guidelines.

## 📋 Table of Contents

### Getting Started

| Document | Purpose | Audience |
|----------|---------|----------|
| [Quick Start Guide](quick-start-guide.md) | Setup for new developers | New developers |
| [Code Standards](code-standards.md) | Python/TypeScript coding guidelines & conventions | All developers |
| [Testing Guide](testing-guide.md) | Testing strategies & patterns | All developers |

### Core Development

| Document | Purpose | Audience |
|----------|---------|----------|
| [**Backend Development Guide**](backend-development.md) | 🏗️ API development, integrations, and architecture | Backend developers |
| [**Database & Architecture Guide**](database-architecture.md) | 🗄️ Database design, schema, and system architecture | Backend developers |
| [Frontend Development](frontend-development.md) | Next.js frontend development guide | Frontend developers |
| [Data Models](data-models.md) | Pydantic models and TypeScript interfaces | All developers |
| [**Branch Conventions**](branch-conventions.md) | 🏗️ Git workflow and branch naming standards | All developers |

### Specialized Topics

| Document | Purpose | Audience |
|----------|---------|----------|
| [**Debugging & Performance Guide**](debugging-performance.md) | 🐛 Debugging techniques, profiling, and optimization | All developers |
| [CI Overview](ci-overview.md) | Continuous integration and deployment | All developers |

## Quick Start

Start with the [Quick Start Guide](quick-start-guide.md) for setup instructions.

### **Essential Commands**

```bash
# Setup (detailed instructions in Quick Start Guide)
uv install                              # Python dependencies
cd frontend && pnpm install             # Frontend dependencies

# Development
uv run python -m tripsage.api.main      # Start API server (localhost:8001)
cd frontend && pnpm dev                 # Start frontend (localhost:3000)

# Testing & Quality
uv run pytest --cov=tripsage           # Backend tests with coverage
cd frontend && pnpm test               # Frontend tests
ruff check . --fix && ruff format .    # Python linting/formatting
npx biome lint --apply .               # TypeScript linting/formatting
```

## 🏗️ Architecture Overview

### **Technology Stack**

- **Backend**: Python 3.13, FastAPI, Pydantic v2
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS  
- **Database**: PostgreSQL (Supabase) + pgvector
- **Caching**: Upstash Redis (HTTP)
- **Testing**: pytest (Python), Vitest (TypeScript), Playwright (E2E)
- **AI/ML**: LangGraph, Mem0, OpenTelemetry

### **Code Quality Standards**

- **Test Coverage**: ≥90% (enforced by CI)
- **Type Safety**: Full type hints (Python), strict TypeScript
- **Linting**: ruff (Python), Biome (TypeScript)
- **Security**: Zero hardcoded secrets, environment variables only
- **Performance**: Sub-second API responses, <1.5s frontend load times

## 🔧 Development Tools

### **Python Development**

```bash
# Linting and formatting
ruff check . --fix
ruff format .

# Testing with coverage
uv run pytest --cov=tripsage --cov-report=html

# Type checking
uv run mypy tripsage
```

### **TypeScript Development**

```bash
# Linting and formatting
npx biome lint --apply .
npx biome format . --write

# Testing
pnpm test          # Unit tests
pnpm test:e2e      # E2E tests
pnpm test:coverage # Coverage report
```

## 📊 Development Metrics

### **Current Status**

- **Backend Tests**: 2,444 tests (79.9% passing)
- **Frontend Tests**: 1,443 tests (64.1% passing)  
- **E2E Tests**: Playwright suite
- **Code Coverage**: 85-90% target coverage
- **Performance**: Sub-1.5s load times, >95 Lighthouse score

### **Success Metrics**

- ✅ Zero critical security vulnerabilities
- ✅ 90%+ test coverage maintained
- ✅ All linting rules pass
- ✅ Type safety enforced
- ✅ Real-time features functional

## 🔗 Related Documentation

- **[Architecture](../03_ARCHITECTURE/README.md)** - High-level system design
- **[API Reference](../06_API_REFERENCE/README.md)** - Public API documentation  
- **[Configuration](../07_CONFIGURATION/README.md)** - Environment & deployment setup
- **[User Guides](../08_USER_GUIDES/README.md)** - End-user documentation

## 🆘 Getting Help

- **New Developer Setup**: Start with [Quick Start Guide](quick-start-guide.md)
- **Database Questions**: Reference [Database & Architecture Guide](database-architecture.md)
- **Performance Issues**: Check [Debugging & Performance Guide](debugging-performance.md)
- **Architecture Questions**: See [Database & Architecture Guide](database-architecture.md)
- **Code Issues**: Check [Debugging & Performance Guide](debugging-performance.md)
- **API Questions**: Reference [Backend Development Guide](backend-development.md)
- **API Key Issues**: See [Database & Architecture Guide](database-architecture.md)
- **Testing Issues**: Consult [Testing Guide](testing-guide.md)

---

*This documentation is designed to help internal developers become productive quickly while maintaining high code quality and consistency across TripSage.*
