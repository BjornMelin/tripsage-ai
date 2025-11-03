# API Usage Examples

This document provides practical examples for integrating with the TripSage API.

## Table of Contents

- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [Flight Search](#flight-search)
- [Accommodation Search](#accommodation-search)
- [Trip Management](#trip-management)
- [Memory System](#memory-system)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)

## Quick Start

### Interactive Documentation

- **Swagger UI**: `http://localhost:8001/api/docs`
- **ReDoc**: `http://localhost:8001/api/redoc`
- **OpenAPI Schema**: `http://localhost:8001/api/openapi.json`

### Health Check

```bash
curl http://localhost:8001/api/health
```

Response:

```json
{
  "status": "healthy",
  "environment": "development",
  "components": [
    {
      "name": "application",
      "status": "healthy",
      "message": "TripSage API is running"
    },
    {
      "name": "database",
      "status": "healthy",
      "latency_ms": 45.2,
      "message": "Database is responsive"
    },
    {
      "name": "cache",
      "status": "healthy",
      "message": "Cache is responsive"
    }
  ]
}
```

## Authentication

TripSage uses Supabase JWT authentication. Users authenticate with Supabase and receive JWT tokens for API access.

### Using JWT Tokens

```bash
# All API requests require Authorization header
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8001/api/trips
```

### JavaScript Example

```javascript
// Get token from Supabase auth
const { data: { session } } = await supabase.auth.getSession();
const token = session?.access_token;

// Use token in API requests
const response = await fetch('/api/trips', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
```

## Flight Search

### Basic Flight Search

```bash
curl -X POST http://localhost:8001/api/flights/search \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "NYC",
    "destination": "LAX",
    "departure_date": "2025-07-15",
    "return_date": "2025-07-22",
    "passengers": 1,
    "cabin_class": "economy"
  }'
```

Response:

```json
{
  "offers": [
    {
      "id": "offer-123",
      "price": {
        "amount": 299.99,
        "currency": "USD"
      },
      "itineraries": [
        {
          "segments": [
            {
              "departure": {
                "iata_code": "JFK",
                "terminal": "8",
                "at": "2025-07-15T08:00:00Z"
              },
              "arrival": {
                "iata_code": "LAX",
                "terminal": "4",
                "at": "2025-07-15T11:30:00Z"
              },
              "carrier_code": "AA",
              "number": "123",
              "duration": "PT5H30M"
            }
          ]
        }
      ]
    }
  ],
  "search_id": "search-789",
  "total_results": 45
}
```

### Get Flight Offer Details

```bash
curl http://localhost:8001/api/flights/offers/offer-123 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Accommodation Search

### Basic Accommodation Search

```bash
curl -X POST http://localhost:8001/api/accommodations/search \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Los Angeles, CA",
    "check_in": "2025-07-15",
    "check_out": "2025-07-22",
    "guests": 2,
    "rooms": 1
  }'
```

Response:

```json
{
  "listings": [
    {
      "id": "listing-789",
      "name": "The Beverly Hills Hotel",
      "type": "hotel",
      "location": {
        "address": "9641 Sunset Blvd, Beverly Hills, CA 90210",
        "coordinates": {
          "latitude": 34.0901,
          "longitude": -118.4065
        }
      },
      "rating": 4.8,
      "price_per_night": {
        "amount": 189.99,
        "currency": "USD"
      },
      "total_price": {
        "amount": 1329.93,
        "currency": "USD"
      },
      "amenities": ["wifi", "pool", "spa", "restaurant", "parking"]
    }
  ],
  "search_id": "search-456",
  "total_results": 127
}
```

### Get Accommodation Details

```bash
curl -X POST http://localhost:8001/api/accommodations/details \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "listing_id": "listing-789"
  }'
```

## Trip Management

### Create Trip

```bash
curl -X POST http://localhost:8001/api/trips \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "European Adventure",
    "description": "Two-week tour of Europe",
    "start_date": "2025-08-01",
    "end_date": "2025-08-14",
    "budget": 5000,
    "destinations": [
      {
        "name": "Paris",
        "country": "France",
        "city": "Paris"
      }
    ],
    "travelers": 2
  }'
```

Response:

```json
{
  "id": "trip-123",
  "title": "European Adventure",
  "status": "planning",
  "created_at": "2025-06-16T10:30:00Z",
  "itinerary": {
    "days": 14,
    "destinations": 1,
    "estimated_cost": 4750
  }
}
```

### Get Trip Details

```bash
curl http://localhost:8001/api/trips/trip-123 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Update Trip

```bash
curl -X PUT http://localhost:8001/api/trips/trip-123 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "budget": 6000,
    "preferences": {
      "budget_tier": "luxury"
    }
  }'
```

### Trip Security

Trip endpoints use automatic access control. The API verifies permissions before processing requests.

```python
# Access levels are automatically enforced
@router.get("/trips/{trip_id}")
async def get_trip(
    trip_id: str,
    access_result: TripReadAccessDep,  # Verifies read access
    principal: RequiredPrincipalDep,
):
    # Access already verified - proceed with operation
    return {"trip_id": trip_id, "access_level": access_result.access_level}
```

## Memory System

### Add Conversation Memory

```bash
curl -X POST http://localhost:8001/api/memory/conversation \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "I prefer window seats on flights"
      }
    ],
    "session_id": "session-123"
  }'
```

### Search Memories

```bash
curl -X POST http://localhost:8001/api/memory/search \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "flight preferences",
    "limit": 10
  }'
```

Response:

```json
{
  "results": [
    {
      "id": "memory-123",
      "content": "User prefers window seats on flights",
      "category": "preferences",
      "relevance_score": 0.95,
      "created_at": "2025-06-16T10:30:00Z"
    }
  ],
  "query": "flight preferences",
  "total": 1
}
```

### Get User Context

```bash
curl http://localhost:8001/api/memory/context \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Rate Limiting

Rate limiting is enforced automatically. Check headers for limit status:

```bash
curl -I http://localhost:8001/api/health \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response headers:

```bash
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642284000
X-RateLimit-Window: 3600
```

### Handle Rate Limits

```javascript
async function makeAPICall(url, options) {
  const response = await fetch(url, options);

  if (response.status === 429) {
    const retryAfter = response.headers.get('Retry-After');
    console.log(`Rate limited. Retry after ${retryAfter} seconds`);

    await new Promise(resolve =>
      setTimeout(resolve, parseInt(retryAfter) * 1000)
    );
    return makeAPICall(url, options);
  }

  return response.json();
}
```

## Error Handling

### Standard Error Response

```json
{
  "error": true,
  "message": "Invalid destination code",
  "code": "VALIDATION_ERROR",
  "type": "validation",
  "errors": [
    {
      "field": "destination",
      "message": "Invalid destination code",
      "type": "value_error"
    }
  ]
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `AUTHENTICATION_ERROR` | 401 | Invalid or expired token |
| `AUTHORIZATION_ERROR` | 403 | Insufficient permissions |
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Too many requests |
| `EXTERNAL_API_ERROR` | 502 | External service unavailable |
| `INTERNAL_ERROR` | 500 | Server error |

### Error Handling Example

```javascript
async function handleAPIResponse(response) {
  if (!response.ok) {
    const error = await response.json();

    switch (error.code) {
      case 'AUTHENTICATION_ERROR':
        // Refresh token or redirect to login
        await refreshToken();
        break;

      case 'RATE_LIMITED':
        const retryAfter = response.headers.get('Retry-After');
        await delay(parseInt(retryAfter) * 1000);
        break;

      case 'VALIDATION_ERROR':
        showValidationErrors(error.errors);
        break;

      default:
        console.error('API Error:', error);
        showErrorMessage('Something went wrong. Please try again.');
    }

    throw new Error(error.message);
  }

  return response.json();
}
```

## Realtime Features

TripSage uses Supabase Realtime for live features. See the [Realtime API guide](realtime-api.md) for details.

```typescript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(url, key);

// Set auth token for private channels
const { data: { session } } = await supabase.auth.getSession();
if (session?.access_token) {
  supabase.realtime.setAuth(session.access_token);
}

// Join private session channel
const channel = supabase.channel(`session:${sessionId}`, {
  config: { private: true }
});

channel
  .on('broadcast', { event: 'chat:message' }, ({ payload }) => {
    console.log('message', payload);
  })
  .subscribe();
```

## Additional Resources

- [Complete API Reference](rest-endpoints.md)
- [Authentication Guide](auth.md)
- [Realtime API Guide](realtime-api.md)
- [Interactive API Docs](http://localhost:8001/api/docs)
