# TripSage Installation and Setup Guide

This guide explains how to set up and run the TripSage AI travel planning platform. TripSage features a unified architecture with a single FastAPI service, Supabase + pgvector database, DragonflyDB caching, and a Next.js 15 frontend.

## System Requirements

- **Python**: 3.12+ (required for modern async features)
- **Node.js**: 18+ (required for Next.js 15)
- **pnpm**: Latest version (preferred package manager)
- **uv**: Latest version (Python package manager)
- **Git**: For cloning the repository
- **Docker**: Optional, for local DragonflyDB

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd tripsage-ai

# Create Python virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
uv pip install -e .

# Install frontend dependencies
cd frontend
pnpm install
cd ..
```

### 2. Environment Configuration

Copy the environment template and configure your services:

```bash
cp .env.example .env
```

Edit `.env` with your service credentials:

```env
# Core Configuration
DEBUG=false
ENVIRONMENT=development
PORT=8000

# AI Services (Required)
OPENAI_API_KEY=your_openai_api_key_here

# Database - Supabase (Required)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here

# Cache - DragonflyDB (Local development)
DRAGONFLY_URL=redis://localhost:6379
DRAGONFLY_PASSWORD=your_secure_password

# External APIs (Optional - for full functionality)
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
DUFFEL_API_KEY=your_duffel_api_key_here
OPENWEATHERMAP_API_KEY=your_openweathermap_api_key_here
```

### 3. Database Setup

TripSage uses Supabase with pgvector for unified storage:

```bash
# Run database migrations
uv run python scripts/database/run_migrations.py

# Verify database connection
uv run python scripts/verification/verify_connection.py
```

### 4. Start Services

#### Option A: Development (Recommended)

```bash
# Terminal 1: Start DragonflyDB (if not using external Redis)
docker-compose up dragonfly

# Terminal 2: Start API server
uv run python -m tripsage.api.main

# Terminal 3: Start frontend
cd frontend
pnpm dev
```

#### Option B: Full Infrastructure

```bash
# Start all infrastructure services
docker-compose up -d

# Start API server
uv run python -m tripsage.api.main

# Start frontend (in another terminal)
cd frontend && pnpm dev
```

### 5. Verify Installation

- **API**: <http://localhost:8000/docs> (FastAPI docs)
- **Frontend**: <http://localhost:3000> (Next.js app)
- **Monitoring**: <http://localhost:3000> (Grafana, if using full stack)

## Architecture Overview

### Unified Backend

- **Single FastAPI service** at `tripsage/api/`
- **LangGraph Phase 3** for agent orchestration
- **PostgreSQL checkpointing** for conversation state
- **Mem0 memory system** with pgvector backend

### Database Stack

- **Supabase**: Primary database with pgvector for embeddings
- **DragonflyDB**: 25x faster Redis-compatible caching
- **No Neo4j**: Eliminated for simplified architecture

### API Integrations

- **7 Direct SDKs**: Google Maps, Duffel, OpenWeather, etc.
- **1 MCP Server**: Airbnb (only remaining MCP)
- **BYOK System**: Bring Your Own Key authentication

### Frontend

- **Next.js 15**: Modern React with App Router
- **TypeScript**: Full type safety
- **Tailwind CSS**: Utility-first styling
- **Zustand**: State management

## Development Workflow

### Code Quality

```bash
# Python (run from project root)
ruff check . --fix && ruff format .
uv run pytest --cov=tripsage

# TypeScript (run from frontend/)
cd frontend
npx biome lint --apply .
npx biome format --write .
npx vitest run --coverage
```

### Testing

```bash
# Backend tests
uv run pytest tests/ --cov=tripsage --cov-report=html

# Frontend tests
cd frontend
pnpm test:run
pnpm test:e2e

# Integration tests
uv run pytest tests/integration/ -v
```

### Adding Dependencies

**Python packages:**

```bash
# Add to pyproject.toml dependencies, then:
uv pip install -e .
```

**Frontend packages:**

```bash
cd frontend
pnpm add package-name
# For dev dependencies:
pnpm add -D package-name
```

## Production Deployment

### Environment Variables

Ensure all production environment variables are set:

- Database connection strings
- API keys for external services
- Security keys and passwords
- Monitoring and logging configuration

### Database Migration

```bash
# Run production migrations
ENVIRONMENT=production uv run python scripts/database/run_migrations.py
```

### Build and Deploy

```bash
# Build frontend
cd frontend
pnpm build

# Start production API
ENVIRONMENT=production uvicorn tripsage.api.main:app --host 0.0.0.0 --port 8000

# Start production frontend
cd frontend
pnpm start
```

## Configuration Details

### BYOK (Bring Your Own Key) System

Users provide their own API keys through the frontend:

- Stored securely in Supabase
- Encrypted at rest
- Validated before use
- Supports: OpenAI, Google Maps, Duffel, OpenWeather

### Memory System (Mem0)

- **Unified memory** across all conversations
- **pgvector embeddings** for semantic search
- **Automatic context** building for agents
- **Persistent storage** in Supabase

### Agent Orchestration (LangGraph)

- **Phase 3 implementation** with PostgreSQL checkpointing
- **State persistence** across sessions
- **Error recovery** and retry logic
- **Parallel agent execution** for performance

## Troubleshooting

### Common Issues

**Database Connection Errors:**

```bash
# Check Supabase connection
uv run python scripts/verification/verify_connection.py

# Check environment variables
grep -E "SUPABASE|DATABASE" .env
```

**DragonflyDB/Redis Issues:**

```bash
# Test cache connection
docker exec -it tripsage-dragonfly redis-cli ping

# Check cache configuration
grep -E "DRAGONFLY|REDIS" .env
```

**Import Errors:**

```bash
# Reinstall in development mode
uv pip install -e .

# Check Python path
python -c "import tripsage; print(tripsage.__file__)"
```

**Frontend Build Issues:**

```bash
cd frontend
# Clear cache and reinstall
rm -rf node_modules .next
pnpm install
pnpm build
```

### Performance Tuning

**Database:**

- Enable pgvector extension in Supabase
- Configure connection pooling
- Monitor query performance

**Caching:**

- Use DragonflyDB for 25x performance improvement
- Configure appropriate TTL values
- Monitor cache hit rates

**Frontend:**

- Enable Next.js 15 Turbopack for development
- Optimize bundle size with tree shaking
- Use React 19 concurrent features

## Getting Help

1. **Check logs**: Both API and frontend provide detailed error logs
2. **Run verification**: Use scripts in `scripts/verification/`
3. **Review documentation**: See `docs/` for detailed guides
4. **Test configuration**: Ensure `.env` variables are correctly set

## Security Considerations

- **Never commit `.env`** files with real credentials
- **Use `.env.example`** as a template only
- **Rotate API keys** regularly
- **Enable HTTPS** in production
- **Configure CORS** appropriately for your domain
