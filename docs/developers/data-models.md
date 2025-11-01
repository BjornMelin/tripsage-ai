# Data Models

Overview of TripSage data structures and validation.

## Core Concepts

TripSage uses Pydantic models for data validation and TypeScript interfaces for type safety. All models include:

- **UUID primary keys** for all entities
- **Timestamps** for creation and updates
- **Soft deletes** using boolean flags
- **Foreign key relationships** with proper constraints

## Key Entities

### Users

- Authentication and profile information
- API key management for external services
- Conversation history and preferences

### Trips

- Travel planning core entity
- Destinations, dates, and preferences
- Status tracking (planning, booked, completed)

### Flights & Accommodations

- Booking details and pricing
- External API integration data
- Status and confirmation tracking

### Conversations

- AI chat history with embeddings
- Semantic search capabilities
- User context for personalization

## Data Flow

1. **Validation**: Pydantic models validate all input data
2. **Storage**: Supabase PostgreSQL with pgvector for embeddings
3. **Retrieval**: Type-safe queries with relationship loading
4. **Caching**: Upstash Redis for performance optimization

## API Integration

Models are automatically validated at API boundaries:

```python
from pydantic import BaseModel
from typing import List, Optional

class TripCreate(BaseModel):
    name: str
    destinations: List[str]
    start_date: str
    budget: Optional[float] = None
```

## Database Schema

Core tables with relationships:

- `users` - User accounts and profiles
- `trips` - Travel plans and itineraries
- `flights` - Flight bookings and details
- `accommodations` - Hotel/car rental bookings
