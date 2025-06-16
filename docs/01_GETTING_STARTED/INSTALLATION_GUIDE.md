# 🚀 Installation Guide

> **Complete Setup Instructions for TripSage AI**  
> Get TripSage running locally or in production with step-by-step instructions

## 📋 Table of Contents

- [📋 System Requirements](#-system-requirements)
- [⚡ Quick Install (Recommended)](#-quick-install-recommended)
- [🐍 Python Installation Options](#-python-installation-options)
- [🌐 Frontend Setup](#-frontend-setup)
- [🔧 Environment Configuration](#-environment-configuration)
- [🗄️ Database Setup](#️-database-setup)
- [⚡ Cache Setup (DragonflyDB)](#-cache-setup-dragonflydb)
- [🚀 Starting Services](#-starting-services)
- [✅ Verification](#-verification)
- [🐳 Docker Installation](#-docker-installation)
- [🔧 Troubleshooting](#-troubleshooting)

---

## 📋 System Requirements

### **Minimum Requirements**

- **🐍 Python**: 3.12 or higher
- **📦 Node.js**: 18+ (for frontend development)
- **🗄️ Database**: Supabase PostgreSQL account
- **⚡ Cache**: DragonflyDB (Redis-compatible)
- **💾 RAM**: 4GB (8GB recommended)
- **💿 Storage**: 10GB free space
- **🌐 Network**: Stable internet connection

### **Supported Operating Systems**

- **🐧 Linux**: Ubuntu 20.04+, CentOS 8+, Debian 11+
- **🍎 macOS**: 11.0+ (Big Sur and later)
- **🪟 Windows**: 10/11 with WSL2 recommended

### **Key Features Overview**

- 🤖 **AI-Powered Planning**: Intelligent travel recommendations
- 💬 **Real-time Chat**: WebSocket-based communication
- 🧠 **Memory System**: Personalized preferences and history
- ✈️ **Flight Integration**: Direct Duffel API integration
- 🏨 **Accommodation Search**: Comprehensive lodging options
- 🗺️ **Location Services**: Google Maps integration
- 🌤️ **Weather Data**: OpenWeatherMap integration
- 📱 **Modern UI**: Next.js 15 + React 19 frontend

---

## ⚡ Quick Install (Recommended)

### **Using UV Package Manager**

TripSage uses `uv` for fast, reliable Python package management:

```bash
# 1. Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone the repository
git clone https://github.com/your-org/tripsage-ai.git
cd tripsage-ai

# 3. Install dependencies and create virtual environment
uv sync

# 4. Activate the virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# 5. Verify installation
uv run python -c "import tripsage; print('TripSage installed successfully!')"
```

**Why UV?**

- ⚡ **10-100x faster** than pip
- 🔒 **Deterministic builds** with lock files
- 🧹 **Automatic dependency resolution**
- 🔄 **Built-in virtual environment management**

---

## 🐍 Python Installation Options

### **Option 1: UV (Recommended)**

See [Quick Install](#-quick-install-recommended) section above.

### **Option 2: Traditional pip**

```bash
# 1. Clone the repository
git clone https://github.com/your-org/tripsage-ai.git
cd tripsage-ai

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# 4. Upgrade pip
python -m pip install --upgrade pip

# 5. Install dependencies
pip install -r requirements.txt

# 6. Install in development mode
pip install -e .
```

### **Option 3: Poetry**

```bash
# 1. Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 2. Clone and setup
git clone https://github.com/your-org/tripsage-ai.git
cd tripsage-ai

# 3. Install dependencies
poetry install

# 4. Activate environment
poetry shell
```

### **Option 4: Conda/Mamba**

```bash
# 1. Create conda environment
conda create -n tripsage python=3.12
conda activate tripsage

# 2. Clone repository
git clone https://github.com/your-org/tripsage-ai.git
cd tripsage-ai

# 3. Install dependencies
pip install -r requirements.txt
pip install -e .
```

---

## 🌐 Frontend Setup

### **Prerequisites**

Ensure you have Node.js 18+ installed:

```bash
# Check Node.js version
node --version  # Should be 18.0.0 or higher

# Install pnpm (recommended)
npm install -g pnpm
```

### **Frontend Installation**

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
pnpm install

# Verify installation
pnpm --version
```

### **Alternative Package Managers**

```bash
# Using npm
npm install

# Using yarn
yarn install

# Using bun (fastest)
bun install
```

---

## 🔧 Environment Configuration

### **1. Create Environment File**

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

### **2. Configure Environment Variables**

Edit `.env` with your settings:

```env
# ===== CORE CONFIGURATION =====
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8001

# ===== DATABASE (SUPABASE) =====
DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres
SUPABASE_URL=https://[project-id].supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# ===== CACHE (DRAGONFLYDB) =====
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_secure_password
REDIS_DB=0

# ===== AI SERVICES =====
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_MAX_TOKENS=4000

# ===== EXTERNAL APIS =====
DUFFEL_API_KEY=duffel_test_...
GOOGLE_MAPS_API_KEY=AIza...
OPENWEATHER_API_KEY=your_openweather_key

# ===== API CONFIGURATION =====
API_TITLE=TripSage API
API_VERSION=1.0.0
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001"]
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# ===== FEATURE FLAGS =====
ENABLE_MEMORY_SYSTEM=true
ENABLE_REAL_TIME_CHAT=true
ENABLE_FLIGHT_SEARCH=true
ENABLE_ACCOMMODATION_SEARCH=true

# ===== MONITORING =====
SENTRY_DSN=https://...@sentry.io/...
ENABLE_TELEMETRY=true
```

### **3. API Key Setup Guide**

#### **Supabase Setup**

1. Go to [supabase.com](https://supabase.com)
2. Create a new project
3. Go to Settings → API
4. Copy your URL and anon key

#### **OpenAI Setup**

1. Go to [platform.openai.com](https://platform.openai.com)
2. Create an API key
3. Add billing information

#### **Duffel Setup (Flights)**

1. Go to [duffel.com](https://duffel.com)
2. Sign up for developer account
3. Get test API key

#### **Google Maps Setup**

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Enable Maps JavaScript API
3. Create API key with restrictions

---

## 🗄️ Database Setup

### **1. Supabase Project Setup**

```bash
# Install Supabase CLI
npm install -g supabase

# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref your-project-id
```

### **2. Run Database Migrations**

```bash
# Run all migrations
uv run python scripts/database/run_migrations.py

# Or run specific migration
uv run python scripts/database/run_migrations.py --migration 001_initial_schema
```

### **3. Verify Database Connection**

```bash
# Test database connectivity
uv run python scripts/verification/verify_connection.py

# Check database schema
uv run python scripts/verification/verify_schema.py
```

### **4. Seed Development Data (Optional)**

```bash
# Add sample data for development
uv run python scripts/database/seed_development_data.py
```

---

## ⚡ Cache Setup (DragonflyDB)

### **Option 1: Docker (Recommended)**

```bash
# Start DragonflyDB container
docker run -d \
  --name tripsage-dragonfly \
  -p 6379:6379 \
  docker.dragonflydb.io/dragonflydb/dragonfly:latest \
  --logtostderr \
  --cache_mode \
  --requirepass your_secure_password

# Verify container is running
docker ps | grep dragonfly
```

### **Option 2: Local Installation**

```bash
# Ubuntu/Debian
wget https://github.com/dragonflydb/dragonfly/releases/latest/download/dragonfly-x86_64.tar.gz
tar -xzf dragonfly-x86_64.tar.gz
sudo mv dragonfly /usr/local/bin/

# Start DragonflyDB
dragonfly --logtostderr --cache_mode --requirepass your_secure_password
```

### **Option 3: Redis (Alternative)**

```bash
# Install Redis
sudo apt install redis-server  # Ubuntu/Debian
brew install redis             # macOS

# Start Redis
redis-server --requirepass your_secure_password
```

### **Verify Cache Connection**

```bash
# Test cache connectivity
uv run python scripts/verification/verify_dragonfly.py

# Test cache performance
uv run python scripts/benchmarks/dragonfly_performance.py
```

---

## 🚀 Starting Services

### **1. Start Backend API**

```bash
# Activate virtual environment
source .venv/bin/activate

# Start the FastAPI server
uv run python -m tripsage.api.main

# Or with auto-reload for development
uv run uvicorn tripsage.api.main:app --reload --host 0.0.0.0 --port 8001
```

**API will be available at:**

- 🌐 **Main API**: <http://localhost:8001>
- 📚 **Interactive docs**: <http://localhost:8001/api/docs>
- 📖 **Alternative docs**: <http://localhost:8001/api/redoc>
- 🔧 **OpenAPI schema**: <http://localhost:8001/api/openapi.json>

### **2. Start Frontend (Optional)**

```bash
# Navigate to frontend directory
cd frontend

# Start development server
pnpm dev

# Or with specific port
pnpm dev --port 3000
```

**Frontend will be available at:**

- 🌐 **Web App**: <http://localhost:3000>

### **3. Start All Services with Docker Compose**

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

---

## ✅ Verification

### **1. Health Checks**

```bash
# Check API health
curl http://localhost:8001/api/health

# Check database health
curl http://localhost:8001/api/health/database

# Check cache health
curl http://localhost:8001/api/health/cache

# Check external APIs
curl http://localhost:8001/api/health/external
```

### **2. Run Test Suite**

```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest tests/unit/          # Unit tests
uv run pytest tests/integration/   # Integration tests
uv run pytest tests/e2e/          # End-to-end tests

# Run with coverage
uv run pytest --cov=tripsage --cov-report=html
```

### **3. Verify Features**

```bash
# Test flight search
curl -X POST http://localhost:8001/api/flights/search \
  -H "Content-Type: application/json" \
  -d '{"origin": "NYC", "destination": "LAX", "departure_date": "2025-07-15"}'

# Test accommodation search
curl -X POST http://localhost:8001/api/accommodations/search \
  -H "Content-Type: application/json" \
  -d '{"location": "New York", "check_in": "2025-07-15", "check_out": "2025-07-16"}'
```

---

## 🐳 Docker Installation

### **Complete Docker Setup**

```bash
# Clone repository
git clone https://github.com/your-org/tripsage-ai.git
cd tripsage-ai

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Build and start all services
docker-compose up --build -d

# View logs
docker-compose logs -f api

# Check service status
docker-compose ps
```

### **Docker Services**

- **🚀 API**: TripSage FastAPI backend
- **🌐 Frontend**: Next.js web application
- **⚡ DragonflyDB**: High-performance cache
- **📊 Monitoring**: Optional observability stack

### **Production Docker Setup**

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d

# Scale API instances
docker-compose -f docker-compose.prod.yml up -d --scale api=3
```

---

## 🔧 Troubleshooting

### **Common Issues**

#### **🔌 Connection Errors**

**Problem**: Cannot connect to API

```bash
curl: (7) Failed to connect to localhost port 8001: Connection refused
```

**Solutions**:

1. Ensure the API server is running: `ps aux | grep uvicorn`
2. Check port configuration in `.env`
3. Verify firewall settings: `sudo ufw status`
4. Check if port is in use: `lsof -i :8001`

#### **🔑 Authentication Errors**

**Problem**: 401 Unauthorized

```json
{
  "error": true,
  "message": "Invalid API key",
  "code": "AUTHENTICATION_ERROR"
}
```

**Solutions**:

1. Verify API key in `.env` file
2. Check Supabase project settings
3. Ensure JWT secret is set correctly
4. Verify token hasn't expired

#### **🗄️ Database Connection Issues**

**Problem**: Database connection failed

```text
FATAL: password authentication failed for user
```

**Solutions**:

1. Verify `DATABASE_URL` in `.env`
2. Check Supabase project status
3. Ensure database is not paused
4. Test connection: `psql $DATABASE_URL`

#### **⚡ Cache Connection Issues**

**Problem**: DragonflyDB connection failed

```text
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solutions**:

1. Start DragonflyDB: `docker start tripsage-dragonfly`
2. Check Redis URL and password in `.env`
3. Verify port 6379 is available: `lsof -i :6379`
4. Test connection: `redis-cli -h localhost -p 6379 ping`

### **Performance Issues**

#### **Slow API Responses**

1. **Check database performance**:

   ```bash
   curl http://localhost:8001/api/health/database
   ```

2. **Monitor cache hit rates**:

   ```bash
   curl http://localhost:8001/api/health/cache
   ```

3. **Review logs for bottlenecks**:

   ```bash
   tail -f logs/api.log | grep "slow"
   ```

#### **High Memory Usage**

1. **Monitor memory usage**:

   ```bash
   docker stats tripsage-api
   ```

2. **Adjust worker processes**:

   ```env
   # In .env
   WORKERS=2  # Reduce if memory constrained
   ```

3. **Enable memory profiling**:

   ```env
   # In .env
   ENABLE_MEMORY_PROFILING=true
   ```

### **Getting Help**

If you're still having issues:

1. **📖 Check Documentation**: [Complete docs](../README.md)
2. **🔍 Search Issues**: [GitHub Issues](https://github.com/your-org/tripsage-ai/issues)
3. **💬 Join Discord**: [Developer Community](https://discord.gg/tripsage)
4. **📧 Email Support**: <support@tripsage.ai>

---

## 🎉 Next Steps

After successful installation:

1. **📚 Read the [User Guide](../08_USER_GUIDES/README.md)** - Learn how to use TripSage
2. **👨‍💻 Check [Developer Guide](../04_DEVELOPMENT_GUIDE/README.md)** - Start developing
3. **🔌 Explore [API Examples](../08_USER_GUIDES/API_USAGE_EXAMPLES.md)** - See code examples
4. **🔧 Review [Configuration](../07_CONFIGURATION/README.md)** - Customize your setup

---

**🎊 Congratulations!** TripSage AI is now installed and ready to help you build amazing travel experiences!

> *Last updated: June 16, 2025*
