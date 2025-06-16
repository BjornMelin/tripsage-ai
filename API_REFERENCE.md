# TripSage AI API Reference

> **Complete API Documentation for TripSage AI**  
> REST API and WebSocket endpoints with authentication, real-time features, and comprehensive examples

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base URLs](#base-urls)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [Core Endpoints](#core-endpoints)
- [Trip Management](#trip-management)
- [Flight Services](#flight-services)
- [Accommodation Services](#accommodation-services)
- [AI Chat & Memory](#ai-chat--memory)
- [WebSocket API](#websocket-api)
- [User Management](#user-management)
- [Configuration](#configuration)
- [SDKs and Libraries](#sdks-and-libraries)

---

## Overview

The TripSage AI API is a RESTful service that provides comprehensive travel planning capabilities powered by artificial intelligence. It features real-time collaboration, intelligent memory, and integrations with major travel services.

### API Features

- 🔐 **Secure Authentication**: JWT tokens and API key support
- 🚀 **High Performance**: Async processing with sub-second response times
- 🧠 **AI-Powered**: LangGraph agents for intelligent recommendations
- 🔄 **Real-time**: WebSocket support for live collaboration
- 📊 **Comprehensive**: Full travel planning lifecycle coverage
- 🌐 **Well-Documented**: OpenAPI 3.0 with interactive documentation

### Architecture

- **Backend**: FastAPI with Python 3.12+
- **Database**: Supabase PostgreSQL with pgvector
- **Cache**: DragonflyDB (25x faster than Redis)
- **AI**: OpenAI GPT-4 with LangGraph orchestration
- **Memory**: Mem0 for intelligent personalization

---

## Authentication

TripSage supports multiple authentication methods for different use cases.

### JWT Authentication (Recommended)

For user-facing applications, use JWT tokens obtained through the authentication endpoints.

```bash
# Login to get JWT token
curl -X POST "https://api.tripsage.ai/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

**Using JWT Token:**
```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  "https://api.tripsage.ai/api/trips"
```

### API Key Authentication

For server-to-server integration, use API keys with specific permissions.

```bash
# Generate API key
curl -X POST "https://api.tripsage.ai/api/user/keys" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Travel App Integration",
    "permissions": ["trips:read", "trips:write", "flights:read"],
    "expires_in_days": 365
  }'
```

**Response:**
```json
{
  "id": "key_123abc",
  "name": "Travel App Integration",
  "key": "ts_live_1234567890abcdef",
  "permissions": ["trips:read", "trips:write", "flights:read"],
  "created_at": "2025-01-15T10:30:00Z",
  "expires_at": "2026-01-15T10:30:00Z"
}
```

**Using API Key:**
```bash
curl -H "Authorization: Bearer ts_live_1234567890abcdef" \
  "https://api.tripsage.ai/api/flights/search"
```

### Permission Scopes

| Scope | Description | Access Level |
|-------|-------------|--------------|
| `trips:read` | View trip information | Read-only |
| `trips:write` | Create and modify trips | Read-write |
| `trips:delete` | Delete trips | Destructive |
| `flights:read` | Search flights | Read-only |
| `accommodations:read` | Search accommodations | Read-only |
| `chat:access` | Use AI chat features | Interactive |
| `memory:read` | Access user memory | Read-only |
| `memory:write` | Update user preferences | Read-write |
| `admin:access` | Administrative functions | Admin |

---

## Base URLs

### Production
- **API Base URL**: `https://api.tripsage.ai`
- **WebSocket**: `wss://api.tripsage.ai`
- **Documentation**: `https://api.tripsage.ai/docs`

### Development
- **API Base URL**: `http://localhost:8001`
- **WebSocket**: `ws://localhost:8001`
- **Documentation**: `http://localhost:8001/api/docs`

### API Versioning

TripSage uses URL path versioning for major API changes:

- **Current Version**: `v1` (default, no prefix required)
- **Chat API**: `/api/v1/chat` (explicitly versioned)
- **Future Versions**: `/api/v2/...` (when available)

---

## Rate Limiting

API requests are rate-limited to ensure fair usage and system stability.

### Default Limits

| Authentication | Requests per Minute | Burst Limit |
|---------------|-------------------|-------------|
| Unauthenticated | 10 | 20 |
| JWT Token | 100 | 200 |
| API Key (Basic) | 200 | 400 |
| API Key (Premium) | 1000 | 2000 |

### Rate Limit Headers

Every API response includes rate limit information:

```bash
curl -I "https://api.tripsage.ai/api/health"

HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1642284000
X-RateLimit-Window: 60
```

### Rate Limit Exceeded

When limits are exceeded, the API returns a `429 Too Many Requests` status:

```json
{
  "error": true,
  "message": "Rate limit exceeded. Try again in 60 seconds.",
  "code": "RATE_LIMIT_EXCEEDED",
  "type": "ratelimit",
  "retry_after": 60
}
```

---

## Error Handling

TripSage uses standard HTTP status codes with consistent error response format.

### Error Response Format

```json
{
  "error": true,
  "message": "Human-readable error description",
  "code": "MACHINE_READABLE_CODE",
  "type": "error_category",
  "details": {
    "field": "specific_field_error",
    "validation_errors": []
  }
}
```

### Common Status Codes

| Code | Description | Common Causes |
|------|-------------|---------------|
| `200` | Success | Request completed successfully |
| `201` | Created | Resource created successfully |
| `400` | Bad Request | Invalid request parameters |
| `401` | Unauthorized | Missing or invalid authentication |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Resource doesn't exist |
| `422` | Unprocessable Entity | Validation errors |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server-side error |
| `503` | Service Unavailable | Service temporarily unavailable |

### Error Types

| Type | Description | Example Codes |
|------|-------------|---------------|
| `authentication` | Authentication failures | `INVALID_TOKEN`, `TOKEN_EXPIRED` |
| `authorization` | Permission denied | `INSUFFICIENT_PERMISSIONS` |
| `validation` | Input validation errors | `REQUIRED_FIELD`, `INVALID_FORMAT` |
| `ratelimit` | Rate limiting | `RATE_LIMIT_EXCEEDED` |
| `external` | External service errors | `FLIGHT_API_UNAVAILABLE` |
| `internal` | Internal server errors | `DATABASE_ERROR` |

### Validation Errors

For `422` responses, detailed validation errors are provided:

```json
{
  "error": true,
  "message": "Request validation failed",
  "code": "VALIDATION_ERROR",
  "type": "validation",
  "errors": [
    {
      "field": "start_date",
      "message": "Start date must be in the future",
      "type": "value_error"
    },
    {
      "field": "destinations",
      "message": "At least one destination is required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Core Endpoints

### Health Check

Monitor API health and status.

#### Check API Health

```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "application": "TripSage API",
  "version": "1.0.0",
  "environment": "production",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### Check MCP Services Health

```http
GET /api/health/mcp
Authorization: Bearer {token}
```

**Response:**
```json
{
  "status": "healthy",
  "available_mcps": ["duffel", "google_maps", "openweather"],
  "enabled_mcps": ["duffel", "google_maps"],
  "last_check": "2025-01-15T10:30:00Z"
}
```

---

## Trip Management

Core trip planning and management functionality.

### Trip Object

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "456e7890-e89b-12d3-a456-426614174000",
  "title": "European Adventure",
  "description": "Two-week tour of Europe's highlights",
  "start_date": "2025-06-01",
  "end_date": "2025-06-14",
  "duration_days": 13,
  "destinations": [
    {
      "name": "Paris",
      "country": "France",
      "city": "Paris",
      "coordinates": {
        "latitude": 48.8566,
        "longitude": 2.3522
      }
    }
  ],
  "preferences": {
    "budget": {
      "total": 5000,
      "currency": "USD",
      "breakdown": {
        "accommodation": 2000,
        "transportation": 1500,
        "food": 1000,
        "activities": 500
      }
    },
    "accommodation_type": "hotel",
    "transportation_preference": "flights",
    "dietary_restrictions": ["vegetarian"],
    "interests": ["culture", "history", "food"]
  },
  "status": "planning",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T12:45:00Z"
}
```

### Create Trip

Create a new trip with AI assistance.

```http
POST /api/trips
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "Tokyo Cherry Blossom Trip",
  "description": "Experience cherry blossom season in Japan",
  "start_date": "2025-04-01",
  "end_date": "2025-04-08",
  "destinations": [
    {
      "name": "Tokyo",
      "country": "Japan",
      "city": "Tokyo",
      "coordinates": {
        "latitude": 35.6762,
        "longitude": 139.6503
      }
    }
  ],
  "preferences": {
    "budget": {
      "total": 3000,
      "currency": "USD"
    },
    "accommodation_type": "hotel",
    "interests": ["culture", "nature", "photography"]
  }
}
```

**Response (201 Created):**
```json
{
  "id": "trip_789xyz",
  "user_id": "user_123abc",
  "title": "Tokyo Cherry Blossom Trip",
  "description": "Experience cherry blossom season in Japan",
  "start_date": "2025-04-01",
  "end_date": "2025-04-08",
  "duration_days": 7,
  "destinations": [...],
  "preferences": {...},
  "status": "planning",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### Get Trip

Retrieve a specific trip by ID.

```http
GET /api/trips/{trip_id}
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "id": "trip_789xyz",
  "user_id": "user_123abc",
  "title": "Tokyo Cherry Blossom Trip",
  "description": "Experience cherry blossom season in Japan",
  "start_date": "2025-04-01",
  "end_date": "2025-04-08",
  "duration_days": 7,
  "destinations": [...],
  "preferences": {...},
  "status": "planning",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### List Trips

Get a paginated list of user's trips.

```http
GET /api/trips?skip=0&limit=10
Authorization: Bearer {token}
```

**Query Parameters:**
- `skip` (integer, optional): Number of trips to skip (default: 0)
- `limit` (integer, optional): Number of trips to return (default: 10, max: 100)

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": "trip_789xyz",
      "title": "Tokyo Cherry Blossom Trip",
      "start_date": "2025-04-01",
      "end_date": "2025-04-08",
      "duration_days": 7,
      "destinations": ["Tokyo"],
      "status": "planning",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 10
}
```

### Update Trip

Update trip details.

```http
PUT /api/trips/{trip_id}
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body (partial updates allowed):**
```json
{
  "title": "Updated Trip Title",
  "end_date": "2025-04-10",
  "preferences": {
    "budget": {
      "total": 3500,
      "currency": "USD"
    }
  }
}
```

### Delete Trip

```http
DELETE /api/trips/{trip_id}
Authorization: Bearer {token}
```

**Response (204 No Content)**

### Trip Suggestions

Get AI-powered trip suggestions based on user preferences.

```http
GET /api/trips/suggestions?limit=4&budget_max=5000&category=culture
Authorization: Bearer {token}
```

**Query Parameters:**
- `limit` (integer): Number of suggestions (1-20, default: 4)
- `budget_max` (float): Maximum budget filter
- `category` (string): Category filter (culture, adventure, relaxation, nature)

**Response (200 OK):**
```json
[
  {
    "id": "suggestion-1",
    "title": "Tokyo Cherry Blossom Adventure",
    "destination": "Tokyo, Japan",
    "description": "Experience the magic of cherry blossom season...",
    "estimated_price": 2800,
    "currency": "USD",
    "duration": 7,
    "rating": 4.8,
    "category": "culture",
    "best_time_to_visit": "March - May",
    "highlights": ["Cherry Blossoms", "Temples", "Street Food"],
    "trending": true,
    "seasonal": true,
    "difficulty": "easy"
  }
]
```

### Trip Collaboration

Share trips with other users for collaborative planning.

#### Share Trip

```http
POST /api/trips/{trip_id}/share
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "user_emails": ["friend@example.com", "family@example.com"],
  "permission_level": "editor",
  "message": "Let's plan this trip together!"
}
```

**Permission Levels:**
- `viewer`: Can view trip details
- `editor`: Can view and edit trip details
- `admin`: Can view, edit, and manage collaborators

**Response (200 OK):**
```json
[
  {
    "user_id": "user_456def",
    "email": "friend@example.com",
    "name": "Jane Smith",
    "permission_level": "editor",
    "added_by": "user_123abc",
    "added_at": "2025-01-15T10:30:00Z",
    "is_active": true
  }
]
```

#### List Collaborators

```http
GET /api/trips/{trip_id}/collaborators
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "collaborators": [
    {
      "user_id": "user_456def",
      "email": "friend@example.com",
      "name": "Jane Smith",
      "permission_level": "editor",
      "added_by": "user_123abc",
      "added_at": "2025-01-15T10:30:00Z",
      "is_active": true
    }
  ],
  "total": 1,
  "owner_id": "user_123abc"
}
```

---

## Flight Services

Search and manage flight options with Duffel API integration.

### Search Flights

Find flight options based on travel criteria.

```http
POST /api/flights/search
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "origin": "JFK",
  "destination": "NRT",
  "departure_date": "2025-04-01",
  "return_date": "2025-04-08",
  "passengers": 2,
  "cabin_class": "economy",
  "budget_max": 1500,
  "preferred_airlines": ["ANA", "JAL"],
  "flexible_dates": {
    "enabled": true,
    "days_before": 2,
    "days_after": 2
  }
}
```

**Response (200 OK):**
```json
{
  "results": [
    {
      "id": "flight_offer_123",
      "airline": "ANA",
      "price": {
        "total": 1280,
        "currency": "USD",
        "breakdown": {
          "base_fare": 1100,
          "taxes": 180
        }
      },
      "outbound": {
        "departure": {
          "airport": "JFK",
          "terminal": "1",
          "time": "2025-04-01T14:30:00Z"
        },
        "arrival": {
          "airport": "NRT",
          "terminal": "1",
          "time": "2025-04-02T17:45:00+09:00"
        },
        "duration": "PT14H15M",
        "stops": 0,
        "aircraft": "Boeing 787-9"
      },
      "return": {
        "departure": {
          "airport": "NRT",
          "terminal": "1",
          "time": "2025-04-08T11:00:00+09:00"
        },
        "arrival": {
          "airport": "JFK",
          "terminal": "1",
          "time": "2025-04-08T09:30:00Z"
        },
        "duration": "PT13H30M",
        "stops": 0,
        "aircraft": "Boeing 787-9"
      },
      "baggage": {
        "carry_on": "1 piece",
        "checked": "2 pieces included"
      },
      "refundable": false,
      "changeable": true,
      "change_fee": 200,
      "booking_deadline": "2025-03-25T23:59:59Z"
    }
  ],
  "search_metadata": {
    "total_results": 45,
    "search_id": "search_789xyz",
    "currency": "USD",
    "searched_at": "2025-01-15T10:30:00Z"
  }
}
```

### Get Flight Details

Retrieve detailed information about a specific flight offer.

```http
GET /api/flights/{flight_offer_id}
Authorization: Bearer {token}
```

### Flight Price Tracking

Track price changes for specific routes.

```http
POST /api/flights/track
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "route": {
    "origin": "JFK",
    "destination": "NRT",
    "departure_date": "2025-04-01",
    "return_date": "2025-04-08"
  },
  "passengers": 2,
  "target_price": 1200,
  "notification_email": "user@example.com"
}
```

---

## Accommodation Services

Search and manage accommodation options.

### Search Accommodations

Find hotels, vacation rentals, and other lodging options.

```http
POST /api/accommodations/search
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "location": "Tokyo, Japan",
  "check_in": "2025-04-01",
  "check_out": "2025-04-08",
  "guests": 2,
  "rooms": 1,
  "budget_max": 200,
  "property_types": ["hotel", "apartment"],
  "amenities": ["wifi", "breakfast", "gym"],
  "star_rating_min": 4,
  "coordinates": {
    "latitude": 35.6762,
    "longitude": 139.6503,
    "radius_km": 10
  },
  "sort_by": "price"
}
```

**Response (200 OK):**
```json
{
  "results": [
    {
      "id": "hotel_123",
      "name": "Tokyo Grand Hotel",
      "property_type": "hotel",
      "star_rating": 4,
      "location": {
        "address": "1-1-1 Shibuya, Shibuya City, Tokyo",
        "coordinates": {
          "latitude": 35.6595,
          "longitude": 139.7004
        },
        "neighborhood": "Shibuya",
        "distance_to_center": 2.5
      },
      "price": {
        "total": 180,
        "per_night": 180,
        "currency": "USD",
        "taxes_included": true,
        "breakdown": {
          "room_rate": 160,
          "taxes": 20
        }
      },
      "room": {
        "type": "Deluxe Double Room",
        "size_sqm": 25,
        "bed_type": "Double",
        "max_guests": 2,
        "description": "Modern room with city view"
      },
      "amenities": [
        "Free WiFi",
        "Breakfast included",
        "Fitness center",
        "Air conditioning",
        "24-hour front desk"
      ],
      "rating": {
        "score": 4.3,
        "max_score": 5.0,
        "review_count": 1248,
        "recent_reviews": [
          {
            "rating": 5,
            "comment": "Great location and service",
            "date": "2025-01-10"
          }
        ]
      },
      "policies": {
        "check_in": "15:00",
        "check_out": "11:00",
        "cancellation": "Free cancellation until 24 hours before check-in",
        "pets_allowed": false
      },
      "images": [
        {
          "url": "https://example.com/hotel1.jpg",
          "caption": "Hotel exterior",
          "type": "exterior"
        }
      ]
    }
  ],
  "search_metadata": {
    "total_results": 156,
    "search_id": "search_456def",
    "currency": "USD",
    "searched_at": "2025-01-15T10:30:00Z"
  }
}
```

### Get Accommodation Details

```http
GET /api/accommodations/{accommodation_id}
Authorization: Bearer {token}
```

---

## AI Chat & Memory

Interactive AI-powered trip planning with intelligent memory.

### Memory System

TripSage's AI memory system learns from interactions to provide personalized recommendations.

#### Get User Memory

```http
GET /api/memory/user
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "user_id": "user_123abc",
  "preferences": {
    "budget_tier": "mid-range",
    "accommodation_type": "boutique_hotels",
    "transportation_preference": "flights",
    "dietary_restrictions": ["vegetarian"],
    "interests": ["culture", "history", "food", "architecture"],
    "travel_style": "immersive_local",
    "group_size_preference": "solo_or_couple"
  },
  "travel_history": {
    "destinations_visited": ["Paris", "Tokyo", "Barcelona"],
    "favorite_seasons": ["spring", "fall"],
    "typical_trip_duration": 7,
    "avg_budget_per_trip": 2500
  },
  "ai_insights": {
    "personality_profile": "Cultural explorer who values authentic experiences",
    "recommendation_factors": [
      "Historical significance",
      "Local food scene",
      "Walkable neighborhoods",
      "Art and museums"
    ]
  },
  "last_updated": "2025-01-15T10:30:00Z"
}
```

#### Update User Preferences

```http
PUT /api/memory/preferences
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "budget_tier": "luxury",
  "interests": ["art", "wine", "wellness"],
  "dietary_restrictions": ["gluten_free"],
  "accommodation_preference": "luxury_resorts"
}
```

### Chat with AI

Start interactive conversations with TripSage AI agents. For real-time chat, use the WebSocket API.

#### Send Chat Message

```http
POST /api/v1/chat/message
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "message": "I want to plan a romantic trip to Italy for my anniversary",
  "session_id": "session_123abc",
  "context": {
    "trip_id": "trip_456def",
    "current_step": "destination_selection"
  },
  "preferences": {
    "budget": 4000,
    "duration_days": 10,
    "travel_style": "romantic"
  }
}
```

**Response (200 OK):**
```json
{
  "message_id": "msg_789xyz",
  "response": "That sounds wonderful! Italy is perfect for a romantic anniversary. Based on your budget and preferences, I'd suggest focusing on 2-3 cities to really savor the experience. Are you drawn more to the artistic treasures of Florence and Rome, or the romantic canals of Venice and coastal beauty of Cinque Terre?",
  "suggestions": [
    {
      "type": "destination",
      "title": "Classic Romance: Rome & Florence",
      "description": "Art, history, and incredible food",
      "estimated_cost": 3200
    },
    {
      "type": "destination", 
      "title": "Coastal Romance: Venice & Cinque Terre",
      "description": "Canals, villages, and seaside charm",
      "estimated_cost": 3600
    }
  ],
  "next_actions": [
    "destination_selection",
    "date_planning",
    "accommodation_preferences"
  ],
  "session_id": "session_123abc",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## WebSocket API

Real-time communication for interactive planning and collaboration.

### Connection

Connect to the WebSocket endpoint with authentication:

```javascript
const ws = new WebSocket('wss://api.tripsage.ai/api/chat/ws?token=YOUR_JWT_TOKEN');

ws.onopen = function(event) {
    console.log('Connected to TripSage Chat');
};

ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log('Received:', message);
};

ws.onerror = function(error) {
    console.error('WebSocket error:', error);
};

ws.onclose = function(event) {
    console.log('WebSocket connection closed:', event.code, event.reason);
};
```

### Message Types

#### Send User Message

```javascript
ws.send(JSON.stringify({
    type: 'user_message',
    content: 'Help me find flights from New York to Tokyo',
    session_id: 'session_123abc',
    context: {
        trip_id: 'trip_456def'
    },
    timestamp: new Date().toISOString()
}));
```

#### AI Response

```json
{
    "type": "ai_response",
    "content": "I'd be happy to help you find flights from New York to Tokyo! Let me search for the best options...",
    "session_id": "session_123abc",
    "agent": "flight_search_agent",
    "suggestions": [
        {
            "type": "flight_search",
            "action": "search_flights",
            "parameters": {
                "origin": "NYC",
                "destination": "NRT"
            }
        }
    ],
    "timestamp": "2025-01-15T10:30:15Z"
}
```

#### System Notifications

```json
{
    "type": "system_notification",
    "content": "Flight prices for your Tokyo trip have dropped by $150",
    "notification_type": "price_alert",
    "data": {
        "trip_id": "trip_456def",
        "price_change": -150,
        "new_price": 1130,
        "currency": "USD"
    },
    "timestamp": "2025-01-15T10:31:00Z"
}
```

#### Typing Indicator

```json
{
    "type": "typing_indicator",
    "user_id": "user_123abc",
    "is_typing": true,
    "session_id": "session_123abc",
    "timestamp": "2025-01-15T10:30:05Z"
}
```

#### Collaboration Events

```json
{
    "type": "collaboration_event",
    "event": "trip_updated",
    "user": {
        "id": "user_456def",
        "name": "Jane Smith"
    },
    "changes": {
        "field": "destinations",
        "action": "added",
        "value": "Kyoto"
    },
    "trip_id": "trip_789xyz",
    "timestamp": "2025-01-15T10:32:00Z"
}
```

### WebSocket Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 1000 | Normal Closure | Normal connection close |
| 1001 | Going Away | Server shutting down |
| 1002 | Protocol Error | Invalid WebSocket frame |
| 1003 | Unsupported Data | Unsupported message type |
| 1008 | Policy Violation | Authentication failed |
| 1011 | Internal Error | Server error |
| 4001 | Authentication Failed | Invalid or expired token |
| 4002 | Rate Limited | Too many messages |
| 4003 | Session Expired | Session timeout |

---

## User Management

User account and profile management endpoints.

### User Profile

#### Get Current User

```http
GET /api/users/me
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "id": "user_123abc",
  "email": "user@example.com",
  "name": "John Doe",
  "profile": {
    "avatar_url": "https://example.com/avatar.jpg",
    "bio": "Passionate traveler and culture enthusiast",
    "location": "San Francisco, CA",
    "website": "https://johndoe.com",
    "social_links": {
      "instagram": "@johndoe",
      "twitter": "@johndoe"
    }
  },
  "preferences": {
    "timezone": "America/Los_Angeles",
    "currency": "USD",
    "language": "en",
    "notifications": {
      "email": true,
      "push": true,
      "price_alerts": true,
      "trip_updates": true
    }
  },
  "subscription": {
    "plan": "premium",
    "status": "active",
    "expires_at": "2025-12-31T23:59:59Z"
  },
  "stats": {
    "trips_planned": 12,
    "countries_visited": 15,
    "total_distance_km": 45678
  },
  "created_at": "2024-01-15T10:30:00Z",
  "last_active": "2025-01-15T09:45:00Z"
}
```

#### Update User Profile

```http
PUT /api/users/me
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "John Doe",
  "profile": {
    "bio": "Adventure seeker and food lover",
    "location": "New York, NY"
  },
  "preferences": {
    "currency": "EUR",
    "notifications": {
      "price_alerts": false
    }
  }
}
```

### Authentication Management

#### Change Password

```http
POST /api/auth/change-password
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "current_password": "old_password",
  "new_password": "new_secure_password"
}
```

#### Refresh Token

```http
POST /api/auth/refresh
Content-Type: application/json
```

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### API Key Management

#### List API Keys

```http
GET /api/user/keys
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "keys": [
    {
      "id": "key_123abc",
      "name": "Travel App Integration",
      "permissions": ["trips:read", "trips:write"],
      "last_used": "2025-01-14T15:30:00Z",
      "created_at": "2025-01-01T10:00:00Z",
      "expires_at": "2026-01-01T10:00:00Z",
      "is_active": true
    }
  ],
  "total": 1
}
```

#### Revoke API Key

```http
DELETE /api/user/keys/{key_id}
Authorization: Bearer {token}
```

---

## Configuration

Application configuration and feature management.

### Feature Flags

#### Get Available Features

```http
GET /api/config/features
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "features": {
    "ai_chat": {
      "enabled": true,
      "description": "AI-powered chat assistance",
      "beta": false
    },
    "real_time_collaboration": {
      "enabled": true,
      "description": "Real-time trip collaboration",
      "beta": false
    },
    "price_tracking": {
      "enabled": true,
      "description": "Flight and hotel price tracking",
      "beta": true
    },
    "advanced_analytics": {
      "enabled": false,
      "description": "Detailed trip analytics",
      "beta": true,
      "required_plan": "premium"
    }
  },
  "user_plan": "basic",
  "region": "us-east-1"
}
```

### System Configuration

#### Get API Configuration

```http
GET /api/config
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "version": "1.0.0",
  "environment": "production",
  "features": {...},
  "limits": {
    "max_trips_per_user": 100,
    "max_collaborators_per_trip": 10,
    "max_destinations_per_trip": 20,
    "file_upload_max_size_mb": 10
  },
  "external_services": {
    "duffel": {
      "available": true,
      "status": "operational"
    },
    "google_maps": {
      "available": true,
      "status": "operational"
    },
    "openweather": {
      "available": true,
      "status": "operational"
    }
  },
  "supported_currencies": ["USD", "EUR", "GBP", "JPY", "CAD", "AUD"],
  "supported_languages": ["en", "es", "fr", "de", "it", "ja", "zh"]
}
```

---

## SDKs and Libraries

Official and community SDKs for popular programming languages.

### JavaScript/TypeScript SDK

```bash
npm install @tripsage/sdk
```

```typescript
import { TripSageClient } from '@tripsage/sdk';

const client = new TripSageClient({
  apiKey: 'ts_live_1234567890abcdef',
  baseUrl: 'https://api.tripsage.ai'
});

// Create a trip
const trip = await client.trips.create({
  title: 'European Adventure',
  startDate: '2025-06-01',
  endDate: '2025-06-14',
  destinations: [
    { name: 'Paris', country: 'France' },
    { name: 'Rome', country: 'Italy' }
  ]
});

// Search flights
const flights = await client.flights.search({
  origin: 'JFK',
  destination: 'CDG',
  departureDate: '2025-06-01',
  passengers: 2
});
```

### Python SDK

```bash
pip install tripsage-python
```

```python
from tripsage import TripSageClient

client = TripSageClient(
    api_key='ts_live_1234567890abcdef',
    base_url='https://api.tripsage.ai'
)

# Create a trip
trip = client.trips.create({
    'title': 'European Adventure',
    'start_date': '2025-06-01',
    'end_date': '2025-06-14',
    'destinations': [
        {'name': 'Paris', 'country': 'France'},
        {'name': 'Rome', 'country': 'Italy'}
    ]
})

# Search flights
flights = client.flights.search({
    'origin': 'JFK',
    'destination': 'CDG',
    'departure_date': '2025-06-01',
    'passengers': 2
})
```

### Go SDK

```bash
go get github.com/tripsage/tripsage-go
```

```go
package main

import (
    "context"
    "github.com/tripsage/tripsage-go"
)

func main() {
    client := tripsage.NewClient("ts_live_1234567890abcdef")
    
    // Create a trip
    trip, err := client.Trips.Create(context.Background(), &tripsage.TripCreateRequest{
        Title:     "European Adventure",
        StartDate: "2025-06-01",
        EndDate:   "2025-06-14",
        Destinations: []tripsage.Destination{
            {Name: "Paris", Country: "France"},
            {Name: "Rome", Country: "Italy"},
        },
    })
    
    if err != nil {
        panic(err)
    }
    
    // Search flights
    flights, err := client.Flights.Search(context.Background(), &tripsage.FlightSearchRequest{
        Origin:        "JFK",
        Destination:   "CDG", 
        DepartureDate: "2025-06-01",
        Passengers:    2,
    })
}
```

### Webhook Integration

TripSage can send webhooks for important events.

#### Configure Webhooks

```http
POST /api/webhooks
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "url": "https://your-app.com/webhooks/tripsage",
  "events": [
    "trip.created",
    "trip.updated", 
    "flight.price_changed",
    "collaboration.added"
  ],
  "secret": "webhook_secret_key"
}
```

#### Webhook Payload Example

```json
{
  "id": "evt_123abc",
  "type": "trip.updated",
  "data": {
    "trip_id": "trip_456def",
    "user_id": "user_789xyz",
    "changes": {
      "destinations": {
        "added": ["Venice"],
        "removed": []
      }
    }
  },
  "created_at": "2025-01-15T10:30:00Z"
}
```

---

## Examples and Tutorials

### Complete Trip Planning Flow

Here's a complete example of planning a trip using the TripSage API:

```javascript
// 1. Authenticate
const authResponse = await fetch('https://api.tripsage.ai/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password'
  })
});
const { access_token } = await authResponse.json();

// 2. Create a trip
const tripResponse = await fetch('https://api.tripsage.ai/api/trips', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    title: 'Japan Adventure',
    startDate: '2025-04-01',
    endDate: '2025-04-08',
    destinations: [{ name: 'Tokyo', country: 'Japan' }],
    preferences: {
      budget: { total: 3000, currency: 'USD' },
      interests: ['culture', 'food']
    }
  })
});
const trip = await tripResponse.json();

// 3. Search flights
const flightResponse = await fetch('https://api.tripsage.ai/api/flights/search', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    origin: 'JFK',
    destination: 'NRT',
    departureDate: '2025-04-01',
    returnDate: '2025-04-08',
    passengers: 1
  })
});
const flights = await flightResponse.json();

// 4. Search accommodations
const hotelResponse = await fetch('https://api.tripsage.ai/api/accommodations/search', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    location: 'Tokyo, Japan',
    checkIn: '2025-04-01',
    checkOut: '2025-04-08',
    guests: 1,
    budgetMax: 200
  })
});
const hotels = await hotelResponse.json();

// 5. Chat with AI for recommendations
const ws = new WebSocket(`wss://api.tripsage.ai/api/chat/ws?token=${access_token}`);
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'user_message',
    content: 'What are the must-see attractions in Tokyo for a culture enthusiast?',
    sessionId: 'session_123',
    context: { tripId: trip.id }
  }));
};
```

---

## Support and Resources

### Getting Help

- **Documentation**: This comprehensive API reference
- **Interactive Docs**: Available at `/api/docs` and `/api/redoc`
- **SDKs**: Official SDKs for popular languages
- **Community**: Join our [Discord server](https://discord.gg/tripsage)
- **Support**: Email support@tripsage.ai
- **Status Page**: [status.tripsage.ai](https://status.tripsage.ai)

### Rate Limits and Quotas

Contact support for higher limits or enterprise pricing:
- **Email**: enterprise@tripsage.ai
- **Custom Limits**: Available for high-volume applications
- **SLA Support**: 99.9% uptime guarantee
- **Dedicated Support**: Priority technical assistance

### Changelog

Stay updated with API changes:
- **API Version**: v1.0.0
- **Last Updated**: 2025-01-15
- **Breaking Changes**: None in current version
- **Deprecations**: Check `/api/config` for upcoming changes

---

**TripSage AI API - Powering the future of intelligent travel planning** ✈️🌟

For the latest updates and announcements, follow [@TripSageAPI](https://twitter.com/tripsageapi) on Twitter.