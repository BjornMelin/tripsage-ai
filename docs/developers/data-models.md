# 📊 TripSage API Data Models

> **Complete Data Structure Reference**  
> Request/response models, validation schemas, and data types for TripSage API

## 📋 Table of Contents

- [Core Travel Models](#core-travel-models)
- [User & Authentication Models](#user--authentication-models)
- [Search & Filter Models](#search--filter-models)
- [AI & Memory Models](#ai--memory-models)
- [Response Models](#response-models)
- [Validation Rules](#validation-rules)
- [Common Types](#common-types)
- [Examples](#examples)

---

## Core Travel Models

### Trip Model

Complete trip information with destinations, preferences, and status.

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
      },
      "arrival_date": "2025-06-01",
      "departure_date": "2025-06-05"
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
  "updated_at": "2025-01-15T12:45:00Z",
  "collaborators": [
    {
      "user_id": "789e0123-e89b-12d3-a456-426614174000",
      "role": "editor",
      "invited_at": "2025-01-15T11:00:00Z"
    }
  ]
}
```

#### Trip Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string (UUID) | Yes | Unique trip identifier |
| `user_id` | string (UUID) | Yes | Trip owner's user ID |
| `title` | string | Yes | Trip title (max 100 chars) |
| `description` | string | No | Trip description (max 1000 chars) |
| `start_date` | string (date) | Yes | Trip start date (ISO 8601) |
| `end_date` | string (date) | Yes | Trip end date (ISO 8601) |
| `duration_days` | integer | No | Calculated trip duration |
| `destinations` | array | Yes | List of destinations (min 1) |
| `preferences` | object | No | Trip preferences |
| `status` | enum | Yes | Trip status |
| `created_at` | string (datetime) | Yes | Creation timestamp |
| `updated_at` | string (datetime) | Yes | Last update timestamp |
| `collaborators` | array | No | Trip collaborators |

#### Trip Status Values

| Status | Description |
|--------|-------------|
| `planning` | Trip is being planned |
| `booked` | Trip is booked and confirmed |
| `active` | Trip is currently happening |
| `completed` | Trip has been completed |
| `cancelled` | Trip has been cancelled |

### Destination Model

Destination information with coordinates and dates.

```json
{
  "name": "Tokyo",
  "country": "Japan",
  "city": "Tokyo",
  "region": "Kanto",
  "coordinates": {
    "latitude": 35.6762,
    "longitude": 139.6503
  },
  "arrival_date": "2025-04-01",
  "departure_date": "2025-04-08",
  "timezone": "Asia/Tokyo",
  "currency": "JPY",
  "language": "ja"
}
```

### Flight Model

Flight information with pricing and booking details.

```json
{
  "id": "flight_123abc",
  "airline": "Japan Airlines",
  "airline_code": "JL",
  "flight_number": "JL006",
  "departure": {
    "airport": {
      "code": "JFK",
      "name": "John F. Kennedy International Airport",
      "city": "New York",
      "country": "United States",
      "timezone": "America/New_York"
    },
    "terminal": "1",
    "gate": "A12",
    "time": "2025-04-01T14:30:00Z"
  },
  "arrival": {
    "airport": {
      "code": "NRT",
      "name": "Narita International Airport",
      "city": "Tokyo",
      "country": "Japan",
      "timezone": "Asia/Tokyo"
    },
    "terminal": "2",
    "gate": "B5",
    "time": "2025-04-02T18:45:00+09:00"
  },
  "duration": "14h 15m",
  "aircraft": {
    "type": "Boeing 777-300ER",
    "configuration": "3-4-3"
  },
  "price": {
    "total": 1250.00,
    "base_fare": 1100.00,
    "taxes": 150.00,
    "currency": "USD"
  },
  "booking_class": "economy",
  "fare_type": "flexible",
  "baggage": {
    "carry_on": {
      "included": true,
      "weight_limit": "10kg",
      "size_limit": "55x40x25cm"
    },
    "checked": {
      "included": 1,
      "weight_limit": "23kg",
      "additional_fee": 50.00
    }
  },
  "amenities": [
    "wifi",
    "entertainment",
    "meals",
    "power_outlets"
  ],
  "cancellation_policy": {
    "refundable": true,
    "change_fee": 100.00,
    "cancellation_fee": 200.00
  }
}
```

### Accommodation Model

Hotel and accommodation information with pricing and amenities.

```json
{
  "id": "hotel_456def",
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
    "distance_to_center": 2.5,
    "nearby_attractions": [
      {
        "name": "Shibuya Crossing",
        "distance": 0.3,
        "type": "landmark"
      }
    ]
  },
  "price": {
    "total": 1260.00,
    "per_night": 180.00,
    "currency": "USD",
    "taxes_included": true,
    "breakdown": {
      "room_rate": 1120.00,
      "taxes": 140.00
    }
  },
  "room": {
    "type": "Deluxe Double Room",
    "size_sqm": 25,
    "bed_type": "Double",
    "max_guests": 2,
    "description": "Modern room with city view",
    "view": "city"
  },
  "amenities": [
    "Free WiFi",
    "Breakfast included",
    "Fitness center",
    "Air conditioning",
    "24-hour front desk",
    "Concierge service"
  ],
  "rating": {
    "score": 4.3,
    "max_score": 5.0,
    "review_count": 1248,
    "recent_reviews": [
      {
        "rating": 5,
        "comment": "Great location and service",
        "date": "2025-01-10",
        "reviewer": "Anonymous"
      }
    ]
  },
  "policies": {
    "check_in": "15:00",
    "check_out": "11:00",
    "cancellation": "Free cancellation until 24 hours before check-in",
    "pets_allowed": false,
    "smoking_allowed": false
  },
  "images": [
    {
      "url": "https://example.com/hotel1.jpg",
      "caption": "Hotel exterior",
      "type": "exterior"
    }
  ]
}
```

---

## User & Authentication Models

### User Model

Complete user profile information.

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "name": "John Doe",
  "avatar_url": "https://example.com/avatar.jpg",
  "email_verified": true,
  "phone": "+1-555-123-4567",
  "phone_verified": false,
  "preferences": {
    "currency": "USD",
    "language": "en",
    "timezone": "America/New_York",
    "units": "metric",
    "notifications": {
      "email": true,
      "push": true,
      "sms": false
    }
  },
  "travel_profile": {
    "frequent_flyer_programs": [
      {
        "airline": "United Airlines",
        "number": "UA123456789",
        "tier": "Gold"
      }
    ],
    "passport": {
      "country": "US",
      "expiry_date": "2030-12-31"
    },
    "dietary_restrictions": ["vegetarian"],
    "accessibility_needs": [],
    "emergency_contact": {
      "name": "Jane Doe",
      "phone": "+1-555-987-6543",
      "relationship": "spouse"
    }
  },
  "subscription": {
    "plan": "premium",
    "status": "active",
    "expires_at": "2025-12-31T23:59:59Z"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2025-01-15T12:45:00Z",
  "last_login": "2025-01-15T09:00:00Z"
}
```

### API Key Model

API key information with permissions and usage.

```json
{
  "id": "key_123abc",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Travel App Integration",
  "description": "API key for mobile app backend",
  "key": "ts_live_1234567890abcdef",
  "key_preview": "ts_live_1234...cdef",
  "permissions": [
    "trips:read",
    "trips:write",
    "flights:read",
    "accommodations:read"
  ],
  "created_at": "2025-01-15T10:30:00Z",
  "expires_at": "2026-01-15T10:30:00Z",
  "last_used": "2025-01-15T12:00:00Z",
  "usage_count": 1247,
  "ip_whitelist": [
    "192.168.1.0/24",
    "10.0.0.1"
  ],
  "status": "active"
}
```

---

## Search & Filter Models

### Flight Search Request

```json
{
  "origin": "JFK",
  "destination": "NRT",
  "departure_date": "2025-04-01",
  "return_date": "2025-04-08",
  "passengers": {
    "adults": 2,
    "children": 0,
    "infants": 0
  },
  "cabin_class": "economy",
  "trip_type": "round_trip",
  "filters": {
    "max_price": 2000,
    "airlines": ["JL", "UA", "AA"],
    "max_stops": 1,
    "departure_time": {
      "earliest": "06:00",
      "latest": "22:00"
    },
    "duration": {
      "max_hours": 20
    }
  },
  "sort_by": "price",
  "limit": 50
}
```

### Accommodation Search Request

```json
{
  "location": "Tokyo, Japan",
  "coordinates": {
    "latitude": 35.6762,
    "longitude": 139.6503,
    "radius_km": 10
  },
  "check_in": "2025-04-01",
  "check_out": "2025-04-08",
  "guests": {
    "adults": 2,
    "children": 0,
    "rooms": 1
  },
  "filters": {
    "price_range": {
      "min": 100,
      "max": 300,
      "currency": "USD"
    },
    "property_types": ["hotel", "apartment"],
    "amenities": ["wifi", "breakfast", "gym"],
    "star_rating_min": 4,
    "guest_rating_min": 8.0
  },
  "sort_by": "price",
  "limit": 50
}
```

---

## AI & Memory Models

### Chat Message Model

AI chat interaction structure.

```json
{
  "id": "msg_123abc",
  "session_id": "session_456def",
  "type": "user_message",
  "content": "I want to plan a romantic trip to Italy",
  "timestamp": "2025-01-15T10:30:00Z",
  "context": {
    "trip_id": "trip_789xyz",
    "current_step": "destination_selection",
    "user_preferences": {
      "budget": 4000,
      "duration_days": 10,
      "travel_style": "romantic"
    }
  },
  "metadata": {
    "user_agent": "TripSage Mobile App v1.2.0",
    "ip_address": "192.168.1.100"
  }
}
```

### AI Response Model

```json
{
  "id": "msg_456def",
  "session_id": "session_456def",
  "type": "ai_response",
  "content": "Italy is perfect for a romantic getaway! Based on your preferences...",
  "timestamp": "2025-01-15T10:30:15Z",
  "agent_info": {
    "agent_type": "trip_planner",
    "model": "gpt-4",
    "confidence": 0.95
  },
  "suggestions": [
    {
      "type": "destination",
      "data": {
        "name": "Venice",
        "country": "Italy",
        "reason": "Perfect for romantic gondola rides"
      }
    }
  ],
  "actions": [
    {
      "type": "search_flights",
      "parameters": {
        "destination": "VCE",
        "dates": "flexible"
      }
    }
  ]
}
```

### User Memory Model

AI memory and preferences for personalization.

```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
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
    "avg_budget_per_trip": 2500,
    "preferred_airlines": ["JL", "UA"],
    "preferred_hotel_chains": ["Marriott", "Hilton"]
  },
  "ai_insights": {
    "personality_profile": "Cultural explorer who values authentic experiences",
    "recommendation_factors": [
      "Historical significance",
      "Local food scene",
      "Walkable neighborhoods",
      "Art and museums"
    ],
    "booking_patterns": {
      "advance_booking_days": 45,
      "price_sensitivity": "medium",
      "flexibility": "high"
    }
  },
  "last_updated": "2025-01-15T10:30:00Z"
}
```

---

## Response Models

### Standard Success Response

```json
{
  "success": true,
  "data": {
    // Response data here
  },
  "metadata": {
    "request_id": "req_123abc",
    "timestamp": "2025-01-15T10:30:00Z",
    "processing_time_ms": 245
  }
}
```

### Paginated Response

```json
{
  "success": true,
  "data": [
    // Array of items
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_items": 156,
    "total_pages": 8,
    "has_next": true,
    "has_previous": false,
    "next_cursor": "cursor_abc123",
    "previous_cursor": null
  },
  "metadata": {
    "request_id": "req_456def",
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

### Error Response

```json
{
  "error": true,
  "message": "Validation failed",
  "code": "VALIDATION_ERROR",
  "type": "validation",
  "details": {
    "field": "start_date",
    "issue": "Date must be in the future"
  },
  "request_id": "req_789xyz",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## Validation Rules

### Common Validation Patterns

#### Date Validation
- **Format**: ISO 8601 (YYYY-MM-DD)
- **Future dates**: Start date must be >= today
- **Date range**: End date must be > start date
- **Max duration**: Trip duration <= 365 days

#### String Validation
- **Trip title**: 1-100 characters, no special chars
- **Description**: 0-1000 characters
- **Email**: Valid email format
- **Phone**: E.164 format (+1234567890)

#### Numeric Validation
- **Budget**: > 0, <= 1,000,000
- **Coordinates**: Latitude [-90, 90], Longitude [-180, 180]
- **Passengers**: Adults >= 1, Children >= 0, Total <= 9

#### Array Validation
- **Destinations**: Min 1, Max 10 destinations
- **Permissions**: Valid permission strings only
- **Amenities**: From predefined list

### Field-Specific Rules

```json
{
  "trip": {
    "title": {
      "required": true,
      "min_length": 1,
      "max_length": 100,
      "pattern": "^[a-zA-Z0-9\\s\\-_]+$"
    },
    "start_date": {
      "required": true,
      "format": "date",
      "minimum": "today"
    },
    "budget.total": {
      "required": false,
      "type": "number",
      "minimum": 0,
      "maximum": 1000000
    }
  },
  "user": {
    "email": {
      "required": true,
      "format": "email",
      "max_length": 255
    },
    "password": {
      "required": true,
      "min_length": 8,
      "pattern": "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).*$"
    }
  }
}
```

---

## Common Types

### Coordinate Type

```json
{
  "latitude": 35.6762,
  "longitude": 139.6503
}
```

### Money Type

```json
{
  "amount": 1250.00,
  "currency": "USD"
}
```

### Date Range Type

```json
{
  "start_date": "2025-04-01",
  "end_date": "2025-04-08"
}
```

### Contact Type

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+1-555-123-4567"
}
```

### Address Type

```json
{
  "street": "123 Main St",
  "city": "New York",
  "state": "NY",
  "postal_code": "10001",
  "country": "US"
}
```

---

## Examples

### Creating a Trip

**Request:**
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
    "interests": ["culture", "food", "nature"]
  }
}
```

### Searching Flights

**Request:**
```json
{
  "origin": "JFK",
  "destination": "NRT",
  "departure_date": "2025-04-01",
  "return_date": "2025-04-08",
  "passengers": {
    "adults": 1
  },
  "cabin_class": "economy",
  "filters": {
    "max_price": 1500,
    "max_stops": 1
  }
}
```

### Chat with AI

**Request:**
```json
{
  "message": "What are the best areas to stay in Tokyo for first-time visitors?",
  "session_id": "session_123",
  "context": {
    "trip_id": "trip_456",
    "current_step": "accommodation_selection"
  }
}
```

---

## Schema Validation

All API requests are validated against JSON schemas. Invalid requests return `422 Unprocessable Entity` with detailed validation errors.

### Example Validation Error

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
      "type": "value_error.date.past",
      "input": "2024-01-01"
    },
    {
      "field": "destinations",
      "message": "At least one destination is required",
      "type": "value_error.list.min_items",
      "input": []
    }
  ]
}
```

For complete schema definitions, see the OpenAPI documentation at `/api/docs`.