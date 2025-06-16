# TripSage AI User Guide

> **Complete User Manual for TripSage AI Travel Planning Platform**  
> Modern AI-powered travel planning with intelligent memory and real-time collaboration

## Table of Contents

- [Getting Started](#getting-started)
- [Installation](#installation)
- [Quick Setup](#quick-setup)
- [Using the API](#using-the-api)
- [WebSocket Chat Interface](#websocket-chat-interface)
- [Authentication](#authentication)
- [Travel Planning Features](#travel-planning-features)
- [AI Memory System](#ai-memory-system)
- [Real-time Collaboration](#real-time-collaboration)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## Getting Started

TripSage AI is a modern travel planning platform that combines artificial intelligence with real-time collaboration to create personalized travel experiences. This guide will walk you through setting up and using TripSage for your travel planning needs.

### System Requirements

- **Python**: 3.12 or higher
- **Node.js**: 18+ (for frontend development)
- **Database**: Supabase PostgreSQL
- **Cache**: DragonflyDB (Redis-compatible)
- **Operating System**: Linux, macOS, or Windows

### Key Features

- 🤖 **AI-Powered Planning**: Intelligent travel recommendations
- 💬 **Real-time Chat**: WebSocket-based communication
- 🧠 **Memory System**: Personalized preferences and history
- ✈️ **Flight Integration**: Direct Duffel API integration
- 🏨 **Accommodation Search**: Comprehensive lodging options
- 🗺️ **Location Services**: Google Maps integration
- 🌤️ **Weather Data**: OpenWeatherMap integration
- 📱 **Modern UI**: Next.js 15 + React 19 frontend

---

## Installation

### Option 1: Using UV (Recommended)

TripSage uses `uv` for fast, reliable Python package management:

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/your-org/tripsage-ai.git
cd tripsage-ai

# Install dependencies and create virtual environment
uv sync

# Activate the virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

### Option 2: Using pip

```bash
# Clone the repository
git clone https://github.com/your-org/tripsage-ai.git
cd tripsage-ai

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Frontend Setup (Optional)

If you're planning to run the full-stack application:

```bash
cd frontend
pnpm install
```

---

## Quick Setup

### 1. Environment Configuration

Create a `.env` file in the project root:

```env
# Core Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Database (Supabase)
DATABASE_URL=postgresql://user:password@host:port/database
DATABASE_PUBLIC_KEY=your_supabase_public_key
DATABASE_SERVICE_KEY=your_supabase_service_key

# Cache (DragonflyDB)
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_redis_password

# AI Services
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o

# External APIs
DUFFEL_API_KEY=your_duffel_api_key
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
OPENWEATHER_API_KEY=your_openweather_api_key

# API Configuration
API_TITLE=TripSage API
API_VERSION=1.0.0
CORS_ORIGINS=["http://localhost:3000"]
```

### 2. Database Setup

Initialize the database with migrations:

```bash
# Run database migrations
uv run python scripts/database/run_migrations.py

# Verify database connection
uv run python scripts/verification/verify_connection.py
```

### 3. Start DragonflyDB (Cache)

Using Docker:

```bash
docker run -d --name tripsage-dragonfly -p 6379:6379 \
  docker.dragonflydb.io/dragonflydb/dragonfly:latest \
  --logtostderr --cache_mode --requirepass your_redis_password

# Verify cache connection
uv run python scripts/verification/verify_dragonfly.py
```

### 4. Start the API Server

```bash
# Start the FastAPI server
uv run python -m tripsage.api.main

# The API will be available at:
# - Main API: http://localhost:8001
# - Interactive docs: http://localhost:8001/api/docs
# - Alternative docs: http://localhost:8001/api/redoc
```

### 5. Start the Frontend (Optional)

```bash
cd frontend
pnpm dev

# Frontend will be available at:
# http://localhost:3000
```

---

## Using the API

### Interactive Documentation

TripSage provides automatic interactive API documentation:

- **Swagger UI**: `http://localhost:8001/api/docs`
- **ReDoc**: `http://localhost:8001/api/redoc`
- **OpenAPI Schema**: `http://localhost:8001/api/openapi.json`

### Basic API Usage

#### Health Check

```bash
curl http://localhost:8001/api/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "version": "1.0.0",
  "environment": "development"
}
```

#### Authentication

TripSage uses API key authentication:

```bash
# Get your API key (replace with actual endpoint)
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use API key in requests
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8001/api/trips
```

#### Search Flights

```bash
curl -X POST http://localhost:8001/api/flights/search \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "NYC",
    "destination": "LAX",
    "departure_date": "2025-02-15",
    "return_date": "2025-02-22",
    "passengers": 1
  }'
```

#### Search Accommodations

```bash
curl -X POST http://localhost:8001/api/accommodations/search \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Los Angeles, CA",
    "check_in": "2025-02-15",
    "check_out": "2025-02-22",
    "guests": 2,
    "budget_max": 200
  }'
```

---

## WebSocket Chat Interface

TripSage provides real-time chat functionality for interactive travel planning.

### Connecting to WebSocket

```javascript
// JavaScript WebSocket connection
const ws = new WebSocket('ws://localhost:8001/api/chat/ws?token=YOUR_TOKEN');

ws.onopen = function(event) {
    console.log('Connected to TripSage Chat');
};

ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log('Received:', message);
};

ws.send(JSON.stringify({
    type: 'user_message',
    content: 'I want to plan a trip to Japan',
    session_id: 'your-session-id'
}));
```

### Message Types

#### User Message
```json
{
  "type": "user_message",
  "content": "Plan a 7-day trip to Paris",
  "session_id": "session-123",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### AI Response
```json
{
  "type": "ai_response",
  "content": "I'd be happy to help plan your Paris trip! Let me suggest some options...",
  "session_id": "session-123",
  "timestamp": "2025-01-15T10:30:15Z",
  "metadata": {
    "agent": "destination_research_agent",
    "confidence": 0.95
  }
}
```

#### System Notification
```json
{
  "type": "system_notification",
  "content": "Flight prices updated for your Paris trip",
  "session_id": "session-123",
  "timestamp": "2025-01-15T10:31:00Z"
}
```

---

## Authentication

### API Key Management

#### Generate API Key

```bash
curl -X POST http://localhost:8001/api/user/keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Travel App",
    "permissions": ["flights:read", "accommodations:read", "trips:write"]
  }'
```

#### List API Keys

```bash
curl http://localhost:8001/api/user/keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Revoke API Key

```bash
curl -X DELETE http://localhost:8001/api/user/keys/{key_id} \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### JWT Authentication

TripSage supports JWT tokens for user authentication:

```bash
# Login to get JWT token
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password"
  }'

# Use JWT token
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8001/api/profile
```

---

## Travel Planning Features

### Trip Creation

Create a new trip with AI assistance:

```bash
curl -X POST http://localhost:8001/api/trips \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "European Adventure",
    "description": "Two-week tour of Europe",
    "start_date": "2025-06-01",
    "end_date": "2025-06-14",
    "budget": 5000,
    "destinations": ["Paris", "Rome", "Barcelona"],
    "travelers": 2,
    "preferences": {
      "accommodation_type": "hotel",
      "budget_tier": "mid-range",
      "interests": ["culture", "food", "history"]
    }
  }'
```

### Flight Search and Booking

#### Search Flights
```bash
curl -X POST http://localhost:8001/api/flights/search \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "JFK",
    "destination": "CDG",
    "departure_date": "2025-06-01",
    "return_date": "2025-06-14",
    "passengers": 2,
    "cabin_class": "economy",
    "budget_max": 1200
  }'
```

#### Get Flight Details
```bash
curl http://localhost:8001/api/flights/{flight_id} \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Accommodation Search

#### Search Hotels and Lodging
```bash
curl -X POST http://localhost:8001/api/accommodations/search \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Paris, France",
    "check_in": "2025-06-01",
    "check_out": "2025-06-05",
    "guests": 2,
    "rooms": 1,
    "budget_max": 200,
    "amenities": ["wifi", "breakfast", "gym"],
    "property_type": "hotel"
  }'
```

### Activity and Destination Search

#### Find Activities
```bash
curl -X GET "http://localhost:8001/api/activities?location=Paris&category=cultural&date=2025-06-02" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Get Destination Information
```bash
curl http://localhost:8001/api/destinations/paris \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## AI Memory System

TripSage includes an advanced AI memory system that learns from your preferences and interactions.

### Memory Features

- **Preference Learning**: Remembers your travel preferences
- **Context Retention**: Maintains conversation context across sessions
- **Personalization**: Adapts recommendations based on history
- **Multi-User Support**: Separate memory spaces for different users

### Viewing Your Memory

```bash
# Get user memory
curl http://localhost:8001/api/memory/user \
  -H "Authorization: Bearer YOUR_API_KEY"

# Get trip-specific memory
curl http://localhost:8001/api/memory/trip/{trip_id} \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Memory Management

```bash
# Update preferences
curl -X PUT http://localhost:8001/api/memory/preferences \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "accommodation_preference": "boutique_hotels",
    "budget_tier": "luxury",
    "dietary_restrictions": ["vegetarian"],
    "interests": ["art", "history", "wine"]
  }'

# Clear memory
curl -X DELETE http://localhost:8001/api/memory/clear \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Real-time Collaboration

TripSage supports real-time collaboration for group travel planning.

### Creating Collaborative Trips

```bash
curl -X POST http://localhost:8001/api/trips/{trip_id}/collaborators \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "friend@example.com",
    "role": "editor",
    "permissions": ["view", "edit", "comment"]
  }'
```

### Real-time Updates

Connect to WebSocket for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8001/api/ws/trip/123?token=YOUR_TOKEN');

ws.onmessage = function(event) {
    const update = JSON.parse(event.data);
    if (update.type === 'trip_update') {
        console.log('Trip updated:', update.data);
    }
};
```

### Comment System

```bash
# Add comment to trip
curl -X POST http://localhost:8001/api/trips/{trip_id}/comments \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "What about visiting the Louvre on day 3?",
    "type": "suggestion"
  }'
```

---

## Configuration

### Environment Variables

Key configuration options:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Deployment environment | `development` | No |
| `DEBUG` | Enable debug mode | `false` | No |
| `DATABASE_URL` | Supabase database URL | - | Yes |
| `DATABASE_PUBLIC_KEY` | Supabase public key | - | Yes |
| `DATABASE_SERVICE_KEY` | Supabase service key | - | Yes |
| `REDIS_URL` | DragonflyDB URL | `redis://localhost:6379` | No |
| `OPENAI_API_KEY` | OpenAI API key | - | Yes |
| `DUFFEL_API_KEY` | Duffel API key | - | Yes |
| `GOOGLE_MAPS_API_KEY` | Google Maps API key | - | Yes |

### API Configuration

```python
# Custom configuration
from tripsage_core.config import Settings

settings = Settings(
    api_title="My Travel App",
    api_version="2.0.0",
    cors_origins=["https://myapp.com"],
    rate_limit_requests=200,
    rate_limit_window=60
)
```

### Feature Flags

Enable/disable features:

```env
# Feature flags
ENABLE_FLIGHTS=true
ENABLE_ACCOMMODATIONS=true
ENABLE_ACTIVITIES=true
ENABLE_MEMORY_SYSTEM=true
ENABLE_REAL_TIME_CHAT=true
```

---

## Troubleshooting

### Common Issues

#### Connection Errors

**Problem**: Cannot connect to API
```bash
curl: (7) Failed to connect to localhost port 8001: Connection refused
```

**Solution**:
1. Ensure the API server is running
2. Check the port configuration
3. Verify firewall settings

#### Authentication Errors

**Problem**: 401 Unauthorized
```json
{
  "error": true,
  "message": "Invalid API key",
  "code": "AUTHENTICATION_ERROR"
}
```

**Solution**:
1. Verify your API key is correct
2. Check API key permissions
3. Ensure API key hasn't expired

#### Database Connection Issues

**Problem**: Database connection failed
```
FATAL:  password authentication failed for user
```

**Solution**:
1. Verify database credentials in `.env`
2. Check Supabase project status
3. Ensure database URL is correct

#### Memory/Cache Issues

**Problem**: DragonflyDB connection failed
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solution**:
1. Start DragonflyDB container
2. Check Redis URL and password
3. Verify network connectivity

### Performance Optimization

#### Rate Limiting

Monitor rate limits:
```bash
curl -I http://localhost:8001/api/health
# Check headers:
# X-RateLimit-Limit: 100
# X-RateLimit-Remaining: 99
# X-RateLimit-Reset: 1642284000
```

#### Caching

Check cache status:
```bash
curl http://localhost:8001/api/health/cache \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Database Performance

Monitor query performance:
```bash
curl http://localhost:8001/api/health/database \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Debugging

#### Enable Debug Mode

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

#### View Logs

```bash
# API logs
tail -f logs/api.log

# Database logs
tail -f logs/database.log

# Chat logs
tail -f logs/chat.log
```

#### Test Endpoints

```bash
# Test authentication
curl -X POST http://localhost:8001/api/auth/test \
  -H "Authorization: Bearer YOUR_API_KEY"

# Test database
curl http://localhost:8001/api/health/database

# Test cache
curl http://localhost:8001/api/health/cache

# Test external APIs
curl http://localhost:8001/api/health/external
```

---

## FAQ

### General Questions

**Q: What makes TripSage different from other travel planning tools?**
A: TripSage combines AI-powered recommendations with real-time collaboration and advanced memory capabilities, providing personalized travel planning that learns from your preferences.

**Q: Is TripSage free to use?**
A: TripSage offers both free and premium tiers. The API has rate limits that vary by plan.

**Q: Can I use TripSage for business travel?**
A: Yes, TripSage supports business travel with features like expense tracking, approval workflows, and company policy integration.

### Technical Questions

**Q: What external APIs does TripSage integrate with?**
A: TripSage integrates with Duffel (flights), Google Maps (locations), OpenWeatherMap (weather), and various accommodation providers.

**Q: How does the AI memory system work?**
A: TripSage uses Mem0 for intelligent memory management, storing preferences, context, and learning patterns in vector embeddings for personalized recommendations.

**Q: Can I self-host TripSage?**
A: Yes, TripSage is designed for self-hosting with Docker support and comprehensive deployment guides.

**Q: What databases does TripSage support?**
A: TripSage primarily uses Supabase PostgreSQL with pgvector for embeddings and DragonflyDB for caching.

### API Questions

**Q: Are there SDKs available?**
A: Currently, TripSage provides a REST API with OpenAPI specifications. SDKs for popular languages are in development.

**Q: What's the rate limit for API calls?**
A: Default rate limits are 100 requests per minute. Higher limits are available with premium plans.

**Q: How do I get support for API integration?**
A: Check the documentation, use the interactive API docs, or contact support at support@tripsage.ai.

### Deployment Questions

**Q: What are the system requirements for production?**
A: Minimum requirements include 4GB RAM, 2 CPU cores, and 20GB storage. Recommended specs depend on usage volume.

**Q: How do I scale TripSage for high traffic?**
A: TripSage supports horizontal scaling with load balancers, multiple API instances, and distributed caching.

**Q: Is TripSage GDPR compliant?**
A: Yes, TripSage includes GDPR compliance features including data export, deletion, and consent management.

---

## Support and Resources

### Getting Help

- **Documentation**: Check this guide and the [Developer Guide](DEVELOPER_GUIDE.md)
- **API Reference**: Use the interactive docs at `/api/docs`
- **Community**: Join our [Discord server](https://discord.gg/tripsage)
- **Issues**: Report bugs on [GitHub Issues](https://github.com/your-org/tripsage-ai/issues)
- **Email**: Contact support@tripsage.ai

### Additional Resources

- [Developer Guide](DEVELOPER_GUIDE.md) - Technical development documentation
- [API Reference](API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Production deployment instructions
- [Configuration Reference](CONFIGURATION_REFERENCE.md) - All configuration options
- [Testing Guide](TESTING_GUIDE.md) - Testing framework documentation

---

**Welcome to TripSage AI - where intelligent travel planning meets cutting-edge technology!** 🌟✈️

For the latest updates and announcements, follow us on [Twitter](https://twitter.com/tripsage) and [LinkedIn](https://linkedin.com/company/tripsage).