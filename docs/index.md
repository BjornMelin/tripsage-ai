# TripSage Documentation

Complete technical documentation for TripSage AI, an AI-powered travel planning platform.

## Documentation by Audience

### End Users

- **[User Guide](users/user-guide.md)** - Complete guide for planning and
  managing trips

### API Developers

- **[API Reference](api/api-reference.md)** - Complete REST API
  documentation with examples
- **[Authentication](api/api-reference.md#authentication)** - JWT and API key authentication
- **[Error Codes](api/error-codes.md)** - Error handling reference
- **[Realtime API](api/realtime-api.md)** - Supabase Realtime integration

### Application Developers

- **[Development Guide](developers/development-guide.md)** - Setup,
  architecture, and best practices
- **[Quick Start](developers/quick-start.md)** - Get development environment
  running
- **[Stores](developers/stores.md)** - Zustand store patterns and composition
- **[Testing Guide](developers/testing-guide.md)** - Testing patterns and
  coverage requirements
- **[Metrics](metrics.md)** - Code metrics and performance benchmarks
- **[Maintenance](maintenance.md)** - Development maintenance checklist

### Operators & DevOps

- **[Operators Reference](operators/operators-reference.md)** -
  Deployment, configuration, and operations
- **[Security Guide](operators/security-guide.md)** - Security
  implementation and best practices
- **[Deployment Guide](operators/deployment-guide.md)** - Production
  deployment procedures

## Quick Setup

### Prerequisites

- Python 3.13+ with uv package manager
- Node.js ≥24 with pnpm ≥9.0.0
- Supabase account (database and authentication)
- Upstash Redis (caching)
- OpenAI API key

### Installation

```bash
# Clone repository
git clone <repository-url>
cd tripsage-ai

# Install dependencies
uv sync
cd frontend && pnpm install && cd ..

# Configure environment
cp .env.example .env

# Start services
uv run python -m tripsage.api.main    # Backend (port 8000)
cd frontend && pnpm dev               # Frontend (port 3000)
```

### Verification

```bash
# Health check
curl http://localhost:8000/api/health

# Interactive API docs
open http://localhost:8000/docs
```

## Key Features

### For End Users

- **AI-Powered Planning**: Natural language trip planning with personalized recommendations
- **Real-Time Search**: Live flight, hotel, and activity search with instant updates
- **Collaborative Planning**: Share trips and plan together with travel companions
- **Budget Management**: Track expenses and manage spending across trip components
- **Mobile Access**: Progressive Web App with offline capabilities

### For Developers

- **REST API**: Complete HTTP API with OpenAPI specification
- **Real-Time Updates**: Supabase Realtime for live collaboration features
- **Authentication**: JWT tokens and API keys with Supabase integration
- **Rate Limiting**: Built-in rate limiting with Redis-backed counters
- **Type Safety**: Full TypeScript support with generated client SDKs

### For Operators

- **Containerized Deployment**: Docker-based deployment with multi-cloud
  support
- **Monitoring**: Built-in health checks and observability with
  OpenTelemetry
- **Security**: Row Level Security, encryption, and comprehensive audit
  logging
- **Scalability**: Horizontal scaling with load balancers and caching layers

## Architecture Overview

TripSage uses a modern, unified architecture:

- **Backend**: FastAPI with Python 3.13+ and async operations
- **Database**: Supabase PostgreSQL with Row Level Security and vector
  extensions
- **Cache**: Upstash Redis (HTTP) for serverless caching
- **Frontend**: Next.js 16 with React 19 and TypeScript
- **Real-Time**: Supabase Realtime with private channels
- **AI**: Vercel AI SDK v6 with complete streaming chat (`/api/chat/*`), memory sync (`/api/memory/sync`), and agent tool calling

## Support & Community

- **Documentation**: Search the user guide or API reference for answers
- **GitHub Issues**: Report bugs and request features
- **Community**: Join discussions and share knowledge

---

**Getting Started**: New to TripSage? Start with the
[User Guide](users/user-guide.md) or
[API Reference](api/api-reference.md).
