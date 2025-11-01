# TripSage Developer Documentation

Developer resources and guidelines for the TripSage platform.

## Getting Started

| Guide | Purpose | When to Use |
|-------|---------|-------------|
| [Quick Start Guide](quick-start-guide.md) | Project setup and development environment | First time contributors |
| [Code Standards](code-standards.md) | Coding guidelines and conventions | All development work |
| [Testing Guide](testing-guide.md) | Testing strategies and patterns | Writing and running tests |

## Core Development

| Guide | Purpose | Primary Audience |
|-------|---------|------------------|
| [Backend Development](backend-development.md) | API development, integrations, architecture | Backend developers |
| [Database Architecture](database-architecture.md) | Database design, schema, data modeling | Backend developers |
| [Frontend Development](frontend-development.md) | Next.js development and patterns | Frontend developers |
| [Data Models](data-models.md) | Data structures and validation | All developers |
| [Branch Conventions](branch-conventions.md) | Git workflow and naming standards | All developers |

## Quality & Operations

| Guide | Purpose | Use Case |
|-------|---------|----------|
| [Debugging & Performance](debugging-performance.md) | Debugging techniques and optimization | Troubleshooting issues |
| [CI Overview](ci-overview.md) | Continuous integration and deployment | Understanding CI/CD |

## Development Workflow

### Setup

```bash
# Install dependencies
uv sync                                    # Python packages
cd frontend && pnpm install               # Node packages

# Start development servers
uv run python -m tripsage.api.main        # API server (port 8000)
cd frontend && pnpm dev                   # Frontend (port 3000)
```

### Code Quality

```bash
# Python
ruff check . --fix && ruff format .        # Lint and format
uv run pytest --cov=tripsage              # Test with coverage

# TypeScript
cd frontend && pnpm lint && pnpm format   # Lint and format
cd frontend && pnpm test                  # Run tests
```

## Architecture Overview

- **Backend**: Python 3.13, FastAPI, Pydantic
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS
- **Database**: PostgreSQL (Supabase) with pgvector
- **Caching**: Upstash Redis (HTTP-based)
- **AI**: LangGraph orchestration, Mem0 memory system

## Key Principles

- **Type Safety**: Full type hints in Python, strict TypeScript
- **Testing**: 90%+ coverage required, comprehensive test suite
- **Security**: Environment variables only, no hardcoded secrets
- **Performance**: Async operations, efficient database queries
- **Documentation**: Code and API documentation auto-generated

## Finding Information

- **New to the project?** → [Quick Start Guide](quick-start-guide.md)
- **Writing code?** → [Code Standards](code-standards.md)
- **Building APIs?** → [Backend Development](backend-development.md)
- **Database work?** → [Database Architecture](database-architecture.md)
- **Having issues?** → [Debugging & Performance](debugging-performance.md)
