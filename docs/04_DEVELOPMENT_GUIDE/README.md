# 👨‍💻 TripSage AI Development Guide

> **Developer Resources & Guidelines**  
> This section contains everything developers need to contribute effectively to TripSage, from coding standards to debugging techniques.

## 📋 Development Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| [Coding Standards](CODING_STANDARDS.md) | Code style & conventions | 👨‍💻 All developers |
| [Testing Strategy](TESTING_STRATEGY.md) | Testing approaches & frameworks | 🧪 Developers, QA |
| [API Development](API_DEVELOPMENT.md) | Backend API development guide | 🔌 Backend developers |
| [Frontend Development](FRONTEND_DEVELOPMENT.md) | Frontend development guide | 🎨 Frontend developers |
| [Database Operations](DATABASE_OPERATIONS.md) | Database development & migrations | 💾 Backend developers |
| [Debugging Guide](DEBUGGING_GUIDE.md) | Debugging techniques & tools | 🔧 All developers |
| [Performance Profiling](PERFORMANCE_PROFILING.md) | Performance analysis & optimization | ⚡ Senior developers |

## 🛠️ Development Stack

### **Core Technologies**

- **Backend**: Python 3.12, FastAPI, Pydantic v2
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS
- **Database**: PostgreSQL (Supabase) + pgvector
- **Caching**: DragonflyDB
- **Memory**: Mem0
- **Orchestration**: LangGraph

### **Development Tools**

- **Python**: uv (package management), ruff (linting/formatting)
- **TypeScript**: Biome (linting/formatting), pnpm (package management)
- **Testing**: pytest (Python), Vitest (TypeScript), Playwright (E2E)
- **Monitoring**: OpenTelemetry, Prometheus, Grafana

## 🚀 Quick Start for Developers

### **1. Environment Setup**

```bash
# Clone repository
git clone [repository-url]
cd tripsage-ai

# Python environment
uv pip install -r requirements.txt

# Frontend environment
cd frontend
pnpm install
```

### **2. Development Workflow**

```bash
# Start development services
docker-compose up -d

# Run backend
uv run python -m tripsage.api.main

# Run frontend (in separate terminal)
cd frontend && pnpm dev

# Run tests
uv run pytest --cov=tripsage
cd frontend && pnpm test
```

### **3. Code Quality**

```bash
# Python linting & formatting
ruff check . --fix
ruff format .

# TypeScript linting & formatting
cd frontend
npx biome lint --apply .
npx biome format . --write
```

## 📊 Development Standards

### **Code Quality Requirements**

- **Test Coverage**: ≥90% (enforced by CI)
- **Type Hints**: Mandatory for all Python functions
- **Linting**: Must pass ruff (Python) and Biome (TypeScript)
- **Documentation**: Docstrings for all public APIs
- **Security**: No secrets in code, use environment variables

### **Git Workflow**

- **Branches**: `feature/*`, `fix/*`, `docs/*`
- **Commits**: Conventional format (`feat:`, `fix:`, `docs:`, etc.)
- **Pull Requests**: Required for all changes to `main`
- **Reviews**: At least one approval required

## 🏗️ Architecture Patterns

### **Backend Patterns**

- **Service Layer**: Business logic separation
- **Repository Pattern**: Data access abstraction
- **Dependency Injection**: FastAPI dependencies
- **Error Handling**: Consistent exception patterns
- **Async/Await**: Throughout the stack

### **Frontend Patterns**

- **Component Structure**: Feature-based organization
- **State Management**: Zustand stores
- **Type Safety**: Zod for runtime validation
- **Error Boundaries**: Graceful error handling
- **Testing**: Component and integration tests

## 🔧 Common Development Tasks

### **Adding a New API Endpoint**

1. Define Pydantic models in `tripsage/api/schemas/`
2. Implement service logic in `tripsage/api/services/`
3. Create router in `tripsage/api/routers/`
4. Add tests in `tests/unit/api/`
5. Update API documentation

### **Adding a New Frontend Feature**

1. Create components in `frontend/src/components/features/`
2. Add types in `frontend/src/types/`
3. Implement stores in `frontend/src/stores/`
4. Create tests in `frontend/src/__tests__/`
5. Update navigation and routing

### **Database Migration**

1. Create migration file in `migrations/`
2. Test migration locally
3. Update database models
4. Add tests for new schema
5. Deploy with rollback plan

## 📚 Learning Resources

### **Internal Documentation**

- **[Architecture](../03_ARCHITECTURE/README.md)** - System design
- **[API Reference](../06_API_REFERENCE/README.md)** - API documentation
- **[Configuration](../07_CONFIGURATION/README.md)** - Environment setup

### **External Resources**

- **FastAPI**: [Official Documentation](https://fastapi.tiangolo.com/)
- **Pydantic v2**: [Official Documentation](https://docs.pydantic.dev/latest/)
- **Next.js 15**: [Official Documentation](https://nextjs.org/docs)
- **LangGraph**: [Official Documentation](https://langchain-ai.github.io/langgraph/)

## 🐛 Debugging & Troubleshooting

### **Common Issues**

- **Import Errors**: Check Python path and virtual environment
- **Database Connection**: Verify environment variables
- **Frontend Builds**: Clear node_modules and reinstall
- **Test Failures**: Check for async/await issues

### **Debugging Tools**

- **Python**: Built-in debugger, pytest fixtures
- **TypeScript**: Browser DevTools, VS Code debugger
- **Database**: pgAdmin, Supabase dashboard
- **Network**: OpenTelemetry tracing

## 🔗 Quick Links

- **🚀 [Getting Started](../01_GETTING_STARTED/README.md)** - Setup guide
- **📋 [Project Overview](../02_PROJECT_OVERVIEW/README.md)** - Project context
- **⚡ [Features](../05_FEATURES_AND_INTEGRATIONS/README.md)** - Feature documentation
- **👥 [User Guides](../08_USER_GUIDES/README.md)** - End-user documentation

## 🆘 Getting Help

- **Code Questions**: Check [Debugging Guide](DEBUGGING_GUIDE.md)
- **Architecture Questions**: See [Architecture](../03_ARCHITECTURE/README.md)
- **API Questions**: Reference [API Documentation](../06_API_REFERENCE/README.md)
- **Setup Issues**: Follow [Getting Started](../01_GETTING_STARTED/README.md)

---

*This development guide is designed to help you become productive quickly while maintaining high code quality and consistency across the TripSage codebase.*
