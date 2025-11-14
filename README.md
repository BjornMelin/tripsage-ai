# 🌟 TripSage AI

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15+-black.svg)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3+-blue.svg)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

<!-- markdownlint-disable MD033 -->
<div align="center">

## **Next-Generation AI-Powered Travel Planning Platform**

**Modern Architecture** • **Agentic Multi-Agent Search** • **Configurable Providers** • **Open-Source**

</div>
<!-- markdownlint-enable MD033 -->

---

TripSage AI is an travel planning platform that combines the power of modern AI agents with rich
all-in-one travel services. Built with FastAPI, Next.js, LangGraph, Supabase, and Upstash Redis, with multi-agent AI orchestration, it provides personalized travel recommendations,
real-time booking capabilities, and intelligent memory management.

## ✨ Key Features

- **AI-Powered Planning**: LangGraph agents with GPT-5 for intelligent
  trip recommendations
- **Flight Integration**: Direct Duffel API integration for real-time
  flight search and booking
- **Accommodation Search**: Accommodation discovery and booking
- **Intelligent Memory**: Mem0-powered user preference learning and context
- **Ultra-Fast Caching**: Upstash Redis (HTTP) for low-latency serverless caching
- **Enterprise Security**: RLS policies and JWT authentication
- **Modern Frontend**: Next.js 16 with App Router, React 19, TypeScript, and Vercel AI SDK v6
- **Real-time Collaboration**: Supabase Realtime (private channels + RLS)

## Quick Start

### Prerequisites

- **Python 3.12+** with uv package manager
- **Node.js 24+** with pnpm
- **PostgreSQL 15+** (or Supabase account)
- **Upstash Redis** for caching (via Vercel integration)

### Installation

```bash
# Clone the repository
git clone https://github.com/BjornMelin/tripsage-ai.git
cd tripsage-ai

# Backend setup
uv sync                                    # Install Python dependencies
cp .env.example .env                       # Configure environment
uv run python scripts/database/setup.py   # Initialize database

# Frontend setup
cd frontend
pnpm install                              # Install Node.js dependencies
cp .env.local.example .env.local          # Configure frontend environment

# Start development servers
uv run python -m tripsage.api.main       # Backend (port 8000)
pnpm dev                                  # Frontend (port 3000)
```

### Verification

```bash
# Health check
curl http://localhost:8000/api/health

# Frontend access
open http://localhost:3000
```

## 🏗️ Architecture

TripSage is built on a modern, unified architecture optimized for performance
and scalability:

- **Backend**: FastAPI with Python 3.12+ and async/await patterns
- **Database**: Supabase PostgreSQL with pgvector for embeddings
- **AI**: OpenAI GPT-4 with LangGraph for agent orchestration
- **Cache**: Upstash Redis (HTTP) for low-latency operations
- **Memory**: Mem0 for intelligent user preference learning
- **Frontend**: Next.js 15 with TypeScript and Tailwind CSS

---

## 📚 Documentation

| Guide | Description |
|-------|-------------|
| **[Complete Documentation](docs/README.md)** | **Organized documentation hub** |
| **[User Guide](docs/users/README.md)** | Complete user manual with API usage examples |
| **[Developer Guide](docs/developers/README.md)** | Development setup, architecture, and best practices |
| **[API Reference](docs/api/README.md)** | Complete REST API and Supabase Realtime documentation |
| **[Security Guide](docs/operators/security-guide.md)** | Security implementation and best practices |
| **[Architecture Guide](docs/architecture/README.md)** | System design and technical architecture |

### Interactive Documentation

- **API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc**: `http://localhost:8000/redoc` (Alternative API documentation)
- **Health Check**: `http://localhost:8000/api/health`

---

## 🏗️ Project Structure

For detailed information about the project structure and module organization, see [docs/architecture/project-structure.md](docs/architecture/project-structure.md).

```text
tripsage-ai/
├── tripsage/                   # API application (FastAPI)
├── tripsage_core/              # Core business logic and services
├── frontend/                   # Next.js application
├── tests/                      # test suite
├── scripts/                    # Database and deployment scripts
├── docker/                     # Runtime compose files and Dockerfiles
├── docs/                       # Documentation
└── supabase/                   # Supabase configuration
```

---

## 🛠️ Development

### Essential Commands

```bash
# Backend Development
uv run python -m tripsage.api.main     # Start API server
uv run pytest                          # Run tests
ruff check . --fix && ruff format .    # Lint and format

# Frontend Development
cd frontend
pnpm dev                               # Start Next.js development server
pnpm test                              # Run Vitest tests (85-90% coverage)
pnpm test:e2e                         # Run Playwright E2E tests
npx biome lint --apply .               # Format TypeScript

# Database Operations
uv run python scripts/database/run_migrations.py    # Run migrations
uv run python scripts/verification/verify_setup.py  # Verify installation
```

## Development Standards

See [Testing Guide](docs/developers/testing-guide.md) and [Code Standards](docs/developers/code-standards.md) for details on testing, linting, and quality gates.

---

## Repository Conventions

- Pre-commit: Ruff (lint/format), Bandit, and Pyright (`uv run pyright`). No MyPy or Black hooks.
- Frontend gates: Biome (`pnpm biome:check`), strict TS (`pnpm type-check`), Vitest (`pnpm test:run`).

## Dependency Injection

TripSage standardises dependency injection on FastAPI `app.state` singletons managed by
[`tripsage/app_state.py`](tripsage/app_state.py).

- Lifespan-managed services: `initialise_app_state()` builds an `AppServiceContainer`
  that wires the database, caches, external providers, and domain services. The
  container is stored on `app.state.services` and cleaned up on shutdown.
- Typed accessors: call `services.get_required_service("flight_service", expected_type=FlightService)`
  for safe retrieval and better type-checking.
- API dependencies: `tripsage/api/core/dependencies.py` exposes `Annotated` helpers
  (e.g. `TripServiceDep`, `MemoryServiceDep`) that resolve services from the container.
- Request handlers: use `request: Request` to access `request.app.state.services` when
  needed. Prefer dependency helpers to keep handlers declarative.
- Rate limiting (SlowAPI): any endpoint decorated with `@limiter.limit(...)` must accept
  `request: Request` (and `response: Response` if headers are injected). For unit tests,
  either invoke via HTTP client or unwrap decorators and pass a synthetic `Request`.
  Example snippet used by tests:

  ```py
  from fastapi import Request

  def build_request(method: str, path: str) -> Request:
      scope = {
          "type": "http", "method": method, "path": path, "scheme": "http",
          "headers": [], "client": ("127.0.0.1", 12345), "server": ("test", 80),
          "query_string": b"",
      }
      async def receive():
          return {"type": "http.request", "body": b"", "more_body": False}
      return Request(scope, receive)
  ```

- Orchestration tools: LangGraph tools call `set_tool_services(container)` during startup
  so shared utilities reuse the same singletons (no ad-hoc instantiation inside tools).
- Testing: pytest fixtures construct lightweight containers with typed mocks. See
  `tests/unit/orchestration/test_utils.py::create_mock_services`.

The legacy `ServiceRegistry` abstraction has been removed. All new modules and tests use
the `AppServiceContainer` pattern to keep DI consistent and explicit.

Schema policy (routers vs. schemas):

- Routers must not declare Pydantic `BaseModel` classes. Place request/response
  models under `tripsage/api/schemas/requests|responses` (or `schemas/*.py` when shared).
- Every endpoint declares a `response_model` and returns instances/serializable
  shapes matching the schema. Prefer enum types and validated fields.
- Centralized schemas avoid drift and enable accurate OpenAPI for client codegen.

---

## 🚢 Deployment

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Production build
docker build -t tripsage-ai .
docker run -p 8000:8000 --env-file .env.production tripsage-ai
```

### Kubernetes Deployment

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -l app=tripsage-ai
```

### Environment Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | ✅ |
| `SUPABASE_URL` | Supabase project URL | ✅ |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | ✅ |
| `OPENAI_API_KEY` | OpenAI API key for AI features | ✅ |
| `DUFFEL_ACCESS_TOKEN` | Duffel API token for flights | ⚠️ |
| `REDIS_URL` | Upstash Redis (TLS) URL for backend (rate limiting/cache) | ⚠️ |
| `UPSTASH_REDIS_REST_URL` | Upstash Redis REST URL (frontend/edge) | ⚠️ |
| `UPSTASH_REDIS_REST_TOKEN` | Upstash Redis REST token (frontend/edge) | ⚠️ |
| `MEM0_API_KEY` | Mem0 API key for memory features | ⚠️ |

✅ Required | ⚠️ Optional (fallback available)

**Notes:**

- Backend (FastAPI) uses a TCP Redis connection for distributed rate limiting and caching. Use your Upstash Redis (TLS) URL in `REDIS_URL`.
- Frontend/Edge (Next.js) uses Upstash REST credentials (`UPSTASH_REDIS_REST_URL`/`TOKEN`) for route-level limits or caching.

---

## 🔌 API Overview

### Core Endpoints

```bash
# Authentication
POST /api/auth/login              # User login
POST /api/auth/register           # User registration
POST /api/auth/refresh            # Token refresh

# Trip Management
GET  /api/trips                   # List user trips
POST /api/trips                   # Create new trip
GET  /api/trips/{id}              # Get trip details
PUT  /api/trips/{id}              # Update trip
DELETE /api/trips/{id}            # Delete trip

# Flight Services
GET  /api/flights/search          # Search flights
POST /api/flights/book            # Book selected flight
GET  /api/flights/bookings        # List user bookings

# AI Chat & Memory
POST /api/chat/completions        # AI chat interface
POST /api/memory/conversation     # Store conversation
GET  /api/memory/context          # Get user context
```

### Realtime Client (Supabase Realtime only - private channel)

```ts
import { createClient } from '@supabase/supabase-js'
const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!)
// authorize realtime with access token via RealtimeAuthProvider in app
const channel = supabase.channel(`user:${userId}`, { config: { private: true } })
channel.on('broadcast', { event: 'chat:message' }, ({ payload }) => console.log(payload))
channel.subscribe()
```

---

## 🤝 Contributing

We welcome contributions! See the [Developer Contributing Guide](docs/developers/contributing.md) for the full workflow, code standards, and testing details.

---

## 📈 Performance

TripSage AI is optimized for high performance and scalability:

- **Response Times**: Sub-200ms for cached requests
- **Throughput**: 1000+ requests/second on standard hardware
- **Caching**: Upstash Redis provides managed serverless caching
- **Database**: pgvector enables fast similarity search for recommendations
- **AI**: Optimized LangGraph agents with streaming responses

### Benchmarks

```bash
# Performance testing
uv run python scripts/performance/benchmark_api.py
uv run python scripts/performance/load_test.py

# Cache performance verification
uv run python scripts/verification/verify_upstash.py
```

---

## 🔒 Security

Security is a top priority for TripSage AI:

- **Authentication**: JWT tokens with configurable expiration
- **Authorization**: Role-based access control (RBAC)
- **Data Protection**: Encrypted sensitive data at rest
- **API Security**: Rate limiting and request validation
- **Dependency Security**: Automated vulnerability scanning

### Security Testing

```bash
# Security verification (ensure no hardcoded secrets)
git grep -i "fallback-secret\|development-only" .  # Should return empty

# Run security tests
uv run pytest tests/security/
```

---

### Service Validation

- **Unified result model**: Both API key validation and external service health checks return an `ApiValidationResult`, eliminating duplicate response types.
- **Context-aware fields**: Validation flows populate `is_valid`, `status`, and `validated_at`, while health probes use `health_status`, `checked_at`, and leave validation-only fields unset (`None`).
- **Shared metadata**: Rate-limit quotas, capability discovery, latency timing, and diagnostic details flow through identical fields for streamlined analytics and caching.
- **Computed insights**: `success_rate_category` and `is_healthy` computed fields provide quick rollups regardless of whether the result originated from validation or monitoring.

---

## 📊 Monitoring & Observability

- **Health Checks**: Endpoint monitoring with health checks
- **Logging**: Structured logging with correlation IDs
- **Metrics**: Custom business metrics and performance tracking
- **Error Tracking**: Detailed error reporting and alerting

---

## License

This project is licensed under the MIT License - see the
[LICENSE](LICENSE) file for details.

---

> Built by **Bjorn Melin** as an exploration of AI-driven travel planning.
