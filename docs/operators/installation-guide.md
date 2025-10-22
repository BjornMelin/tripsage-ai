# TripSage Installation Guide

>
> **Complete Setup and Dependencies for TripSage AI Platform**
> Local Development | Docker | Dependencies | Node.js Compatibility
>
> IMPORTANT: This repository is standardized on `pyproject.toml` + `uv`
> for Python dependencies.
> Any references to `requirements.txt` or `requirements-dev.txt` are deprecated
> and will be removed.
> Use `uv sync` (and `uv sync --group dev`) instead.

## Table of Contents

- [TripSage Installation Guide](#tripsage-installation-guide)
  - [Table of Contents](#table-of-contents)
  - [Local Development Setup](#local-development-setup)
  - [Quick Start](#quick-start)
    - [1. Clone and Setup](#1-clone-and-setup)
    - [2. Environment Configuration](#2-environment-configuration)
    - [3. Database Setup](#3-database-setup)
    - [4. Start Services](#4-start-services)
      - [Option A: Development (Recommended)](#option-a-development-recommended)
      - [Option B: Full Infrastructure](#option-b-full-infrastructure)
    - [5. Verify Installation](#5-verify-installation)
  - [Architecture Overview](#architecture-overview)
    - [Unified Backend](#unified-backend)
    - [Database Stack](#database-stack)
    - [API Integrations](#api-integrations)
    - [Frontend](#frontend)
  - [Development Workflow](#development-workflow)
    - [Code Quality](#code-quality)
    - [Testing](#testing)
    - [Dependency Management](#dependency-management)
      - [File Structure](#file-structure)
      - [Adding New Dependencies](#adding-new-dependencies)
      - [Updating Dependencies](#updating-dependencies)
      - [Rationale](#rationale)
  - [Production Deployment](#production-deployment)
    - [Environment Variables](#environment-variables)
    - [Database Migration](#database-migration)
    - [Build and Deploy](#build-and-deploy)
  - [Configuration Details](#configuration-details)
    - [BYOK (Bring Your Own Key) System](#byok-bring-your-own-key-system)
    - [Memory System (Mem0)](#memory-system-mem0)
    - [Agent Orchestration (LangGraph)](#agent-orchestration-langgraph)
  - [Troubleshooting](#troubleshooting)
    - [Common Issues](#common-issues)
    - [Performance Tuning](#performance-tuning)
  - [Getting Help](#getting-help)
  - [Security Considerations](#security-considerations)
  - [Node.js Compatibility](#nodejs-compatibility)
  - [How It Works](#how-it-works)
  - [Server Types](#server-types)
    - [Node.js-based MCP Servers](#nodejs-based-mcp-servers)
    - [Python-based MCP Servers](#python-based-mcp-servers)
  - [Dependency Checking](#dependency-checking)
  - [Version Requirements](#version-requirements)
  - [Troubleshooting (Node.js)](#troubleshooting-nodejs)
    - [Node.js not found](#nodejs-not-found)
    - [npx not found](#npx-not-found)
    - [Version Manager Issues](#version-manager-issues)
  - [Best Practices](#best-practices)
  - [Example Usage](#example-usage)

---

## Local Development Setup

- **uv**: Recommended but optional (modern Python package manager -
  10-100x faster than pip)
- **Git**: For cloning the repository
- **Docker**: Optional, for local DragonflyDB

> **Note**: While `uv` is recommended for its speed and reliability,
> you can use standard `pip` if preferred.

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/BjornMelin/tripsage-ai.git
cd tripsage-ai

# Install uv (recommended):
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or with pip: pip install uv

# Install Python dependencies via pyproject.toml and uv:

# Option 1: Using uv with pyproject.toml (Recommended - Fastest ~30 seconds)
uv sync                    # Install core dependencies only
uv sync --group dev       # Install all dependencies including dev tools


source .venv/bin/activate               # On Windows: .venv\Scripts\activate
# Then install dependencies:
# Or install as editable package:

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
DUFFEL_ACCESS_TOKEN=your_duffel_access_token_here
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

- **API**: [FastAPI docs](http://localhost:8000/docs)
- **Frontend**: [Next.js app](http://localhost:3000)
- **Monitoring**: Jaeger UI at <http://localhost:16686>; OTEL Collector for OTLP

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

### Dependency Management

TripSage standardizes on modern dependency management with `pyproject.toml`
and `uv`. Traditional `requirements.txt` files are not used.

#### File Structure

- **`pyproject.toml`**: The source of truth for all dependencies
  - Core dependencies in `[project.dependencies]`
  - Development dependencies in `[dependency-groups]`
  
- **`uv.lock`**: Locked dependency resolution committed to the repo

#### Adding New Dependencies

**Important**: Always update dependencies in `pyproject.toml`.
`uv` will manage the lockfile.

**Python packages:**

```bash
# Add to pyproject.toml in the appropriate section, then:
uv sync                          # Install the new dependency

uv add <package>
uv add --group dev <package>
```

**Frontend packages:**

```bash
cd frontend
pnpm add package-name            # For production dependencies
pnpm add -D package-name         # For dev dependencies
```

#### Updating Dependencies

```bash
# Update all dependencies to latest compatible versions
uv sync --resolution=highest

# Update a specific package
uv add package-name@latest
```

#### Rationale

1. **KISS/DRY/YAGNI**: Single source of truth avoids drift and duplication.
2. **Performance**: `uv` offers fast installs and reproducible `uv.lock`.
3. **Consistency**: Aligns local, CI, and containers on the same toolchain.

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

---

## Node.js Compatibility

1. **nvm (Node Version Manager)**
   - Popular version manager for Node.js
   - [nvm](https://github.com/nvm-sh/nvm)
   - Automatically sets up PATH for Node.js and npm/npx

2. **fnm (Fast Node Manager)**
   - Rust-based alternative to nvm
   - [fnm](https://github.com/Schniz/fnm)
   - Works seamlessly with our MCP servers

3. **volta**
   - JavaScript toolchain manager
   - [volta](https://volta.sh/)
   - Provides automatic project-based Node.js versions

4. **asdf**
   - Multi-language version manager
   - [asdf](https://asdf-vm.com/)
   - Supports Node.js through plugins

5. **System Package Managers**
   - Ubuntu/Debian: `apt install nodejs`
   - macOS: `brew install node`
   - Windows: Chocolatey, Scoop

6. **Official Node.js Installer**
   - Direct download from [Node.js](https://nodejs.org/)
   - Includes npm and npx by default

## How It Works

The MCP launcher uses `npx` command, which is included with npm
(Node Package Manager). The `npx` command works identically across all
Node.js installation methods because:

1. All Node version managers add their Node.js installation to the system PATH
2. `npx` is a standard tool included with npm since version 5.2
3. The launcher uses `npx -y <package>` to automatically download and run packages

## Server Types

### Node.js-based MCP Servers

These servers require Node.js to be installed:

- Supabase MCP
- Neo4j Memory MCP
- Duffel Flights MCP
- Airbnb MCP
- Google Maps MCP
- Time MCP
- Weather MCP
- Google Calendar MCP
- Firecrawl MCP

### Python-based MCP Servers

These servers don't require Node.js:

- Crawl4AI MCP
- Custom Python MCP servers

## Dependency Checking

The MCP launcher automatically checks for Node.js availability on startup.
If Node.js is not found, it will:

1. Log a warning with installation instructions
2. Provide links to various installation methods
3. Continue running (Python-based servers will still work)

Example output when Node.js is missing:

```plaintext
Node.js not found in PATH. Node-based MCP servers will not work.
Please install Node.js using one of the following:
  - Official installer: [https://nodejs.org/](https://nodejs.org/)
  - Package manager: brew install node (macOS)
  - nvm: [https://github.com/nvm-sh/nvm](https://github.com/nvm-sh/nvm)
  - fnm: [https://github.com/Schniz/fnm](https://github.com/Schniz/fnm)
```

## Version Requirements

- **Minimum Node.js version**: 16.x
- **Recommended Node.js version**: 18.x or 20.x (LTS)
- **npm/npx version**: 5.2+ (included with Node.js)

## Troubleshooting (Node.js)

### Node.js not found

If you see "Node.js not found in PATH":

1. Verify Node.js is installed: `node --version`
2. Check if npm/npx is available: `npx --version`
3. Ensure your Node version manager has been properly initialized in your shell

### npx not found

If Node.js is installed but npx is missing:

1. Update npm: `npm install -g npm@latest`
2. Install npx separately: `npm install -g npx`

### Version Manager Issues

For nvm users:

```bash
# Add to ~/.bashrc, ~/.zshrc, etc.
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
```

For fnm users:

```bash
# Add to shell configuration
eval "$(fnm env)"
```

## Best Practices

1. **Use an LTS Node.js version** for stability
2. **Keep npm updated** to ensure npx compatibility
3. **Set up your version manager** in your shell configuration
4. **Test the installation** by running: `npx -v`

## Example Usage

Once Node.js is properly installed (through any method), MCP servers can be launched:

```bash
# Using the unified launcher
python scripts/mcp/mcp_launcher.py start supabase

# Individual scripts also work
./scripts/startup/start_time_mcp.sh

# Direct npx usage (what the launcher does internally)
npx -y supabase-mcp
```

All these methods will work regardless of how you installed Node.js.
