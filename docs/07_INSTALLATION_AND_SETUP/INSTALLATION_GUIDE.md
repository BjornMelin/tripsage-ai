# TripSage Installation and Usage Guide

This guide explains how to set up your development environment, install dependencies, and run the TripSage project and its components. TripSage uses `uv` as its primary Python package manager and virtual environment tool.

## 1. Prerequisites

- **Python 3.10+**
- **`uv` Package Manager**
- **Git**
- **Node.js** (Optional, for Next.js frontend)
- **Docker** (Recommended for Redis/Neo4j containers)

### Installing `uv`

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

Check with `uv --version`.

## 2. Project Setup

```bash
git clone <repo-url>
cd tripsage-ai
```

### 2.2. Create & Activate Virtual Environment

```bash
uv venv
source .venv/bin/activate  # macOS/Linux (bash/zsh)
```

## 3. Install Dependencies

- **Using `pyproject.toml`**:

```bash
uv pip install -e .  # Or uv pip install -e ".[dev]"
```

- **Or `requirements.txt`**:

```bash
uv pip install -r requirements.txt
```

## 4. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your credentials
```

## 5. Running Project Components

### 5.1. Backend API (FastAPI)

```bash
uvicorn main:app --reload --port 8000
```

### 5.2. MCP Servers

Python-based or Node.js-based. See docs in `docs/04_MCP_SERVERS/`.

### 5.3. Database Services (Docker)

```bash
docker-compose up -d redis neo4j
```

## 6. Development Workflow

- **Lint/Format**: `ruff check . --fix`
- **Type Checking**: `mypy src/`
- **Tests**: `pytest`

## 7. Troubleshooting

- **ModuleNotFoundError**: Check `.venv` activation, installation steps.
- **Env Var Issues**: `.env` not loaded or missing keys.
- **DB Connection**: Ensure Docker services are up.
- **`uv` Not Found**: Add `uv` install path to `PATH`.

This guide helps you quickly get TripSage running locally.
