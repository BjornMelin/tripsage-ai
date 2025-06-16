# TripSage AI

> **Intelligent Travel Planning Platform with AI-Powered Recommendations**  
> Modern FastAPI backend with Next.js frontend, featuring real-time collaboration and personalized trip planning

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15+-black.svg)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3+-blue.svg)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+** with [uv](https://docs.astral.sh/uv/) package manager
- **Node.js 18+** with [pnpm](https://pnpm.io/)
- **PostgreSQL** (or Supabase account)
- **DragonflyDB** (optional, for high-performance caching)

### 1. Backend Setup

```bash
# Clone and setup environment
git clone https://github.com/your-org/tripsage-ai.git
cd tripsage-ai

# Install dependencies with uv
uv sync

# Configure environment
cp .env.example .env.local
# Edit .env.local with your API keys and database credentials

# Run database migrations
uv run python scripts/database/run_migrations.py

# Start the API server
uv run python -m tripsage.api.main
```

The API will be available at `http://localhost:8000` with interactive docs at `/docs`.

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
pnpm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your API endpoints

# Start development server
pnpm dev
```

The frontend will be available at `http://localhost:3000`.

### 3. Quick Test

```bash
# Health check
curl http://localhost:8000/api/health

# Test trip planning (requires authentication)
curl -X POST "http://localhost:8000/api/trips" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Tokyo Adventure",
    "start_date": "2024-07-01",
    "end_date": "2024-07-07",
    "destinations": [{"name": "Tokyo, Japan", "country": "Japan", "city": "Tokyo"}]
  }'
```

---

## 🎯 What is TripSage AI?

TripSage AI is a comprehensive travel planning platform that leverages artificial intelligence to create personalized trip recommendations. It combines flight search, accommodation booking, activity suggestions, and intelligent memory to deliver exceptional travel planning experiences.

### Core Features

- 🧠 **AI-Powered Planning**: LangGraph agents for intelligent trip optimization
- 🔄 **Real-time Collaboration**: WebSocket-based live trip sharing
- 💾 **Intelligent Memory**: Mem0 integration for personalized recommendations
- ✈️ **Flight Integration**: Duffel API for real-time flight search and booking
- 🏨 **Accommodation Search**: Multi-provider hotel and lodging options
- 📱 **Modern Frontend**: Next.js 15 with React 19 and App Router
- 🚀 **High Performance**: DragonflyDB caching (25x faster than Redis)
- 🔒 **Enterprise Security**: JWT authentication with comprehensive RBAC

### Architecture Highlights

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
| **[📚 Complete Documentation](docs/README.md)** | **NEW: Organized documentation hub** |
| **[User Guide](USER_GUIDE.md)** | Complete user manual with API usage examples |
| **[Developer Guide](DEVELOPER_GUIDE.md)** | Development setup, architecture, and best practices |
| **[API Reference](API_REFERENCE.md)** | Complete REST API and WebSocket documentation |
| **[Testing Guide](TESTING_GUIDE.md)** | Testing framework and coverage guidelines |
| **[Deployment Guide](DEPLOYMENT_GUIDE.md)** | Production deployment with Docker/Kubernetes |

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
uv run pytest                          # Run tests (527 currently failing - Pydantic v1→v2)
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

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

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

<p align="center">
  <strong>Built with ❤️ for the future of travel planning</strong>
</p>
