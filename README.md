# 🌟 TripSage AI

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)]
(<https://python.org>)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)]
(<https://fastapi.tiangolo.com>)
[![Next.js](https://img.shields.io/badge/Next.js-15+-black.svg)]
(<https://nextjs.org>)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3+-blue.
svg)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)]
(LICENSE)

> **Next-Generation AI-Powered Travel Planning Platform**  
> Modern Architecture | Production Ready | Comprehensive Documentation

TripSage AI is an intelligent travel planning platform that combines the power of
modern AI agents with comprehensive travel services. Built with FastAPI, Next.js,
and advanced AI orchestration, it provides personalized travel recommendations,
real-time booking capabilities, and intelligent memory management.

## ✨ Key Features

- 🤖 **AI-Powered Planning**: LangGraph agents with GPT-4 for intelligent
  trip recommendations
- ✈️ **Flight Integration**: Direct Duffel API integration for real-time
  flight search and booking
- 🏨 **Accommodation Search**: Comprehensive accommodation discovery and booking
- 🧠 **Intelligent Memory**: Mem0-powered user preference learning and context
- ⚡ **Ultra-Fast Caching**: DragonflyDB for sub-millisecond response times
- 🔒 **Enterprise Security**: Comprehensive RLS policies and JWT authentication
- 📱 **Modern Frontend**: Next.js 15 with React 19 and TypeScript
- 🌐 **Real-time Collaboration**: WebSocket-powered trip sharing and updates

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+** with uv package manager
- **Node.js 20+** with pnpm
- **PostgreSQL 15+** (or Supabase account)
- **Redis/DragonflyDB** for caching

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/tripsage-ai.git
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
- **Cache**: DragonflyDB for sub-millisecond response times
- **Memory**: Mem0 for intelligent user preference learning
- **Frontend**: Next.js 15 with TypeScript and Tailwind CSS

---

## 📚 Documentation

| Guide | Description |
|-------|-------------|
| **[📚 Complete Documentation](docs/README.md)** | **Organized documentation hub** |
| **[User Guide](docs/08_USER_GUIDES/README.md)** | Complete user manual with API usage examples |
| **[Developer Guide](docs/04_DEVELOPMENT_GUIDE/README.md)** | Development setup, architecture, and best practices |
| **[API Reference](docs/06_API_REFERENCE/README.md)** | Complete REST API and WebSocket documentation |
| **[Security Guide](docs/07_CONFIGURATION/SECURITY/README.md)** | Security implementation and best practices |
| **[Architecture Guide](docs/03_ARCHITECTURE/README.md)** | System design and technical architecture |

### Interactive Documentation

- **API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc**: `http://localhost:8000/redoc` (Alternative API documentation)
- **Health Check**: `http://localhost:8000/api/health`

---

## 🏗️ Project Structure

```text
tripsage-ai/
├── tripsage/                    # API application
│   ├── api/                     # FastAPI routers and middleware
│   │   ├── routers/            # API endpoints (trips, flights, chat)
│   │   ├── middlewares/        # Authentication and CORS
│   │   └── core/               # Dependencies and configuration
│   └── tools/                  # AI agent tools and utilities
├── tripsage_core/              # Core business logic
│   ├── services/               # Business and infrastructure services
│   ├── models/                 # Pydantic models and schemas
│   └── exceptions/             # Custom exception handling
├── frontend/                   # Next.js application
│   ├── app/                    # App Router pages and layouts
│   ├── components/             # Reusable React components
│   └── lib/                    # Utilities and API clients
├── tests/                      # Comprehensive test suite
│   ├── unit/                   # Unit tests with 90%+ coverage
│   ├── integration/            # Service integration tests
│   └── e2e/                    # End-to-end Playwright tests
└── scripts/                    # Database and deployment scripts
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

### Testing

The project maintains high testing standards with comprehensive coverage:

- **Unit Tests**: 90%+ coverage with pytest and modern fixtures
- **Integration Tests**: Service-level testing with real dependencies
- **E2E Tests**: Playwright browser automation for user workflows
- **Performance Tests**: Load testing for API endpoints

```bash
# Run specific test suites
uv run pytest tests/unit/           # Unit tests only
uv run pytest tests/integration/    # Integration tests
uv run pytest --cov=tripsage_core   # Coverage report
```

### Code Quality

- **Python**: PEP-8 compliant with ruff formatting (≤88 char lines)
- **TypeScript**: Biome for linting and formatting
- **Type Safety**: Full type hints for Python, strict TypeScript
- **Documentation**: Google-style docstrings for all public APIs

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
| `DRAGONFLY_URL` | DragonflyDB connection string | ⚠️ |
| `MEM0_API_KEY` | Mem0 API key for memory features | ⚠️ |

✅ Required | ⚠️ Optional (fallback available)

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

### WebSocket Connection

```javascript
// Real-time trip collaboration
const ws = new WebSocket('ws://localhost:8000/ws/trip/123e4567-e89b-12d3-a456-426614174000');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Trip update:', message);
};

// Send trip updates
ws.send(JSON.stringify({
  type: 'trip_update',
  data: { title: 'Updated Trip Name' }
}));
```

---

## 🤝 Contributing

We welcome contributions! Please see our
[Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Workflow

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Write** tests for your changes
4. **Ensure** all tests pass (`uv run pytest`)
5. **Format** code (`ruff format . && npx biome format . --write`)
6. **Commit** your changes (`git commit -m 'Add amazing feature'`)
7. **Push** to your branch (`git push origin feature/amazing-feature`)
8. **Open** a Pull Request

### Code Standards

- Follow TDD (Test-Driven Development) principles
- Maintain 90%+ test coverage
- Use conventional commit messages
- Write comprehensive documentation

---

## 📈 Performance

TripSage AI is optimized for high performance and scalability:

- **Response Times**: Sub-200ms for cached requests
- **Throughput**: 1000+ requests/second on standard hardware
- **Caching**: DragonflyDB provides 25x faster performance than Redis
- **Database**: pgvector enables fast similarity search for recommendations
- **AI**: Optimized LangGraph agents with streaming responses

### Benchmarks

```bash
# Performance testing
uv run python scripts/performance/benchmark_api.py
uv run python scripts/performance/load_test.py

# Cache performance verification
uv run python scripts/verification/verify_dragonfly.py
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

## 📊 Monitoring & Observability

- **Health Checks**: Comprehensive endpoint monitoring
- **Logging**: Structured logging with correlation IDs
- **Metrics**: Custom business metrics and performance tracking
- **Error Tracking**: Detailed error reporting and alerting

---

## 📜 License

This project is licensed under the MIT License - see the
[LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **FastAPI** for the excellent async web framework
- **Next.js** for the modern React framework
- **Supabase** for the PostgreSQL backend and authentication
- **OpenAI** for the AI capabilities
- **Duffel** for flight search and booking integration
- **Mem0** for intelligent memory management

---

## 📞 Support

- **Documentation**: Check our comprehensive guides above
- **Issues**: [GitHub Issues](https://github.com/your-org/tripsage-ai/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/tripsage-ai/discussions)
- **Email**: <support@tripsage.ai>

---

## Built with ❤️ for the future of travel planning
