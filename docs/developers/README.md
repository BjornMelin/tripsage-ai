# Developer Documentation

Resources and guidelines for TripSage development.

## Getting Started

| Guide | Purpose |
|-------|---------|
| [Quick Start](quick-start.md) | Project setup and development environment |
| [Code Standards](code-standards.md) | Coding guidelines and conventions |
| [Import Paths](import-paths.md) | TypeScript import path aliases and conventions |
| [Development Guide](development-guide.md) | API routes, state management, and patterns |
| [Stores](stores.md) | Zustand store patterns and composition |
| [Zod Schema Guide](zod-schema-guide.md) | Schema validation and type inference patterns |
| [Testing Guide](testing-guide.md) | Testing strategies and patterns |
| [Activities](activities.md) | Activity search service, tools, and API usage |

## Development

| Guide | Purpose |
|-------|---------|
| [Development Guide](development-guide.md) | Backend, frontend, database, API patterns, and observability |
| [Observability](observability.md) | Telemetry spans, `[operational-alert]` contracts, and alerting guidance |
| [Troubleshooting](troubleshooting.md) | Debugging, CI/CD, and workflow guidance |

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

## Architecture

- **Backend**: Python 3.13, FastAPI, Pydantic
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS
- **Database**: PostgreSQL (Supabase) with pgvector
- **Cache**: Upstash Redis (HTTP REST API)
- **AI**: Vercel AI SDK v6 with frontend-only agents

## Key Principles

- **Type Safety**: Full type hints in Python, strict TypeScript
- **Async First**: All I/O operations use async/await
- **Security**: Environment variables only, JWT authentication
- **Testing**: Comprehensive test coverage required
- **Performance**: Efficient database queries and caching

## Finding Information

- **New to the project?** → [Quick Start](quick-start.md)
- **Writing code?** → [Code Standards](code-standards.md)
- **Building features?** → [Development Guide](development-guide.md)
- **Having issues?** → [Troubleshooting](troubleshooting.md)
