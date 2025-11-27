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

- **[Development Guide](development/development-guide.md)** - Setup,
  architecture, and best practices
- **[Quick Start](development/quick-start.md)** - Get development environment
  running
- **[Standards](development/standards.md)** - Code style, import paths, schemas, stores
- **[Zod Schema Guide](development/zod-schema-guide.md)** - Zod v4 schema patterns, validation, and AI SDK tool schemas
- **[Testing](development/testing.md)** - Strategy, patterns, and templates
- **[AI Integration](development/ai-integration.md)** - Gateway/BYOK options for Vercel AI SDK v6
- **[Metrics](metrics.md)** - Code metrics and performance benchmarks
- **[Maintenance](maintenance.md)** - Development maintenance checklist

### Operators & DevOps

- **[Operators Reference](operations/operators-reference.md)** -
  Deployment, configuration, and operations
- **[Security Guide](operations/security-guide.md)** - Security
  implementation and best practices
- **[Deployment Guide](operations/deployment-guide.md)** - Production
  deployment procedures

## Quick Setup

### Prerequisites

- Node.js ≥24 with pnpm ≥9.0.0
- Supabase account (database and authentication)
- Upstash Redis (caching)
- AI provider API key (OpenAI, Anthropic, or xAI)

### Installation

```bash
# Clone repository
git clone <repository-url>
cd tripsage-ai

# Install dependencies
cd frontend && pnpm install

# Configure environment
cp .env.example .env
# Edit .env with your Supabase, Upstash, and AI provider credentials

# Start development server
pnpm dev
```

### Verification

```bash
# Frontend + API available at
open http://localhost:3000

# Test API endpoint
curl http://localhost:3000/api/dashboard
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

- **Backend**: Next.js 16 server-first route handlers (TypeScript)
- **Database**: Supabase PostgreSQL with Row Level Security and vector
  extensions
- **Cache**: Upstash Redis (HTTP) for serverless caching
- **Frontend**: Next.js 16 with React 19 and TypeScript
- **Real-Time**: Supabase Realtime with private channels
- **AI**: Vercel AI SDK v6 with streaming chat and agent tool calling

## Support & Community

- **Documentation**: Search the user guide or API reference for answers
- **GitHub Issues**: Report bugs and request features
- **Community**: Join discussions and share knowledge

---

**Getting Started**: New to TripSage? Start with the
[User Guide](users/user-guide.md) or
[API Reference](api/api-reference.md).
