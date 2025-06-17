# 👨‍💻 TripSage Developers Documentation

> **Internal Developer Resources & Guidelines**  
> Comprehensive development documentation for TripSage AI team members and contributors.

## 📋 Table of Contents

| Document | Purpose | Audience |
|----------|---------|----------|
| [Code Standards](code-standards.md) | Python/TypeScript coding guidelines & conventions | All developers |
| [Testing Guide](testing-guide.md) | Comprehensive testing strategies & patterns | All developers |
| [API Development](api-development.md) | Backend API development with FastAPI | Backend developers |
| [Frontend Development](frontend-development.md) | Next.js frontend development guide | Frontend developers |
| [Database Operations](database-operations.md) | PostgreSQL, migrations, and data management | Backend developers |
| [Architecture Guide](architecture-guide.md) | System design & database architecture | Senior developers |
| [Debugging Guide](debugging-guide.md) | Debugging techniques & troubleshooting | All developers |
| [Performance Profiling](performance-profiling.md) | Performance analysis & optimization | Senior developers |
| [Contributing Guidelines](contributing-guidelines.md) | Git workflow, code review, and contribution standards | All developers |
| [Local Development Setup](local-development-setup.md) | Environment setup and development workflow | New developers |

## 🛠️ Quick Start

### **Prerequisites**
- Python 3.13+
- Node.js 20+
- PostgreSQL (via Supabase)
- Docker (optional)

### **Development Environment Setup**

```bash
# Clone and setup
git clone [repository-url]
cd tripsage-ai

# Python environment
uv install

# Frontend environment  
cd frontend && pnpm install

# Database setup
# See local-development-setup.md for complete instructions
```

### **Development Workflow**

```bash
# Start services
docker-compose up -d  # Optional: DragonflyDB cache

# Backend development
uv run python -m tripsage.api.main

# Frontend development (separate terminal)
cd frontend && pnpm dev

# Run tests
uv run pytest --cov=tripsage
cd frontend && pnpm test
```

## 🏗️ Architecture Overview

### **Technology Stack**

- **Backend**: Python 3.13, FastAPI, Pydantic v2
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS  
- **Database**: PostgreSQL (Supabase) + pgvector
- **Caching**: DragonflyDB
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
- **E2E Tests**: Comprehensive Playwright suite
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

- **Architecture Questions**: See [Architecture Guide](architecture-guide.md)
- **Code Issues**: Check [Debugging Guide](debugging-guide.md)
- **Setup Problems**: Follow [Local Development Setup](local-development-setup.md)
- **API Questions**: Reference [API Development](api-development.md)
- **Testing Issues**: Consult [Testing Guide](testing-guide.md)

---

*This documentation is designed to help internal developers become productive quickly while maintaining high code quality and consistency across TripSage.*