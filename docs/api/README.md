# TripSage API Documentation

Internal API documentation for the TripSage travel planning platform. This API serves both the frontend application and AI agents with endpoints for authentication, trip management, flight/accommodation search, chat, and real-time communication.

## Quick Start

### Development Environment

```bash
# Start the API server
uv run python -m tripsage.api.main

# API available at:
# - Main API: http://localhost:8000
# - Documentation: http://localhost:8000/docs
# - Alternative docs: http://localhost:8000/redoc
```

### First API Call

```bash
# Health check (no auth required)
curl http://localhost:8000/api/health

# Response:
# {"status": "healthy", "timestamp": "...", "version": "1.0.0"}
```

## API Documentation

### Core References

| Document                                                     | Description                               | Focus               |
| ------------------------------------------------------------ | ----------------------------------------- | ------------------- |
| **[REST API Reference](rest-endpoints.md)**                  | Complete endpoint documentation           | All endpoints       |
| **[Realtime (Supabase)](realtime-api.md)** | Real-time communication and collaboration | Private channels (Supabase Realtime) |
| **[Usage Examples](usage-examples.md)**                      | Practical code snippets                   | Quick reference     |
| **[Error Codes](error-codes.md)**                            | Error handling reference                  | Troubleshooting     |

### Specialized Guides

- **[Dashboard API](dashboard-api.md)** - Monitoring and analytics endpoints

## Authentication

TripSage supports multiple authentication approaches:

| Method     | Use Case                 | Security | Expiration                         |
| ---------- | ------------------------ | -------- | ---------------------------------- |
| JWT Tokens | User apps                | High     | 1 hour (access), 30 days (refresh) |
| API Keys   | Server-to-server         | High     | Configurable (up to 1 year)        |
| OAuth 2.0  | Third-party integrations | High     | Provider-specific                  |

### JWT Authentication (Primary)

#### User Login Flow

```bash
# Register user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secure_password"}'

# Login to get JWT
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secure_password"}'

# Use JWT token
curl http://localhost:8000/api/trips \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Token Management

- **Access tokens**: Short-lived (1 hour), used for API requests
- **Refresh tokens**: Long-lived (30 days), used to get new access tokens
- **Automatic refresh**: Implement in your client application

### API Key Authentication (BYOK)

#### Bring Your Own Keys

Store and manage third-party API keys securely:

```bash
# Add API key
curl -X POST http://localhost:8000/api/keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Duffel API Key",
    "service": "duffel",
    "key": "duffel_test_your_api_key_here"
  }'

# Use API key
curl http://localhost:8000/api/flights/search \
  -H "X-API-Key: YOUR_STORED_API_KEY"
```

#### Supported Services

- **duffel**: Flight search and booking
- **google_maps**: Maps and location services
- **openweather**: Weather information

### Security Best Practices

#### Token Security

- Store tokens securely (httpOnly cookies, secure storage)
- Implement automatic token refresh
- Validate tokens on each request
- Use HTTPS in production

#### API Key Management

- Rotate keys regularly
- Use descriptive names for organization
- Set appropriate expiration dates
- Monitor usage patterns

#### Rate Limiting

Default limits (requests per minute):

- Unauthenticated: 10
- JWT tokens: 100
- API keys: 200-1000 (based on tier)

### Implementation Examples

#### Frontend (React/Next.js)

```typescript
// JWT authentication
const login = async (email: string, password: string) => {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const { access_token } = await response.json();
  localStorage.setItem("token", access_token);
};

// API requests with auth
const apiRequest = async (url: string, options = {}) => {
  const token = localStorage.getItem("token");
  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${token}`,
    },
  });
};
```

#### Backend (Python)

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(credentials = Depends(security)):
    # Validate JWT token and return user
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY)
        return payload['sub']
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Common Issues

#### Token Expired

```json
{
  "error": true,
  "message": "Token has expired",
  "code": "TOKEN_EXPIRED"
}
```

**Solution**: Use refresh token to get new access token

#### Invalid API Key

```json
{
  "error": true,
  "message": "API key not found",
  "code": "API_KEY_NOT_FOUND"
}
```

**Solution**: Verify API key is stored and valid

#### Rate Limited

```json
{
  "error": true,
  "message": "Rate limit exceeded",
  "code": "RATE_LIMIT_EXCEEDED"
}
```

**Solution**: Implement exponential backoff and respect rate limits

## Core Endpoints

### Trip Management

- `GET /api/v1/trips` - List user trips
- `POST /api/v1/trips` - Create new trip
- `GET /api/v1/trips/{id}` - Get trip details
- `PUT /api/v1/trips/{id}` - Update trip
- `DELETE /api/v1/trips/{id}` - Delete trip

### Flight Operations

- `POST /api/v1/flights/search` - Search flights
- `GET /api/v1/flights/{id}` - Get flight details
- `POST /api/v1/flights/{id}/book` - Book flight
- `GET /api/v1/flights/bookings` - List user bookings

### Accommodation Operations

- `POST /api/v1/accommodations/search` - Search accommodations
- `GET /api/v1/accommodations/{id}` - Get details
- `POST /api/v1/accommodations/{id}/book` - Book accommodation

### AI & Chat

- `POST /api/v1/chat/completions` - AI chat interface (non-streaming)
- `POST /api/chat/stream` - Streaming chat via Server-Sent Events (`text/event-stream`)
- `POST /api/v1/memory/conversation` - Store conversation
- `GET /api/v1/memory/context` - Get user context

### Real-time Communication

TripSage uses Supabase Realtime with private channels and RLS. No custom WebSocket endpoints are exposed by the FastAPI backend. Clients authenticate with Supabase and subscribe to authorized channels.

## Development Tools

### Interactive Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

### Testing

```bash
# Run API tests
uv run pytest tests/unit/tripsage/api/ --cov=tripsage.api

# Run integration tests
uv run pytest tests/integration/api/
```

## Response Formats

### Success Response

```json
{
  "data": {...},
  "meta": {
    "request_id": "req_123",
    "timestamp": "2025-06-17T10:30:00Z"
  }
}
```

### Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {...}
  },
  "meta": {
    "request_id": "req_456",
    "timestamp": "2025-06-17T10:30:00Z"
  }
}
```

## Troubleshooting

| Issue                  | Solution               | Reference                                                |
| ---------------------- | ---------------------- | -------------------------------------------------------- |
| `401 Unauthorized`     | Check JWT token format | [Authentication](#authentication)                        |
| `422 Validation Error` | Verify required fields | [Error Codes](error-codes.md)                            |
| `429 Rate Limited`     | Check rate limits      | [Authentication](#authentication)                        |
| Realtime channel disconnect | Refresh access token and resubscribe | [Supabase Realtime Guide](realtime-api.md) |

---

**Need help?** Check the [Usage Examples](usage-examples.md) for practical code samples or the [REST API Reference](rest-endpoints.md) for complete endpoint documentation.
