# 📚 TripSage AI API Reference

> **Technical Reference Documentation**  
> This section provides comprehensive technical reference for TripSage's APIs, data models, and integration patterns.

## 📋 API Documentation

| Document | Purpose | Technical Level |
|----------|---------|-----------------|
| [REST API Endpoints](REST_API_ENDPOINTS.md) | REST API complete reference | 🔌 Complete reference |
| [WebSocket API](WEBSOCKET_API.md) | WebSocket API reference | ⚡ Real-time features |
| [Database Schema](DATABASE_SCHEMA.md) | Complete database schema | 💾 Data modeling |
| [Error Codes](ERROR_CODES.md) | Error handling & status codes | 🚨 Error reference |
| [Authentication API](AUTHENTICATION_API.md) | Authentication endpoints | 🔒 Security |
| [Data Models](DATA_MODELS.md) | Request/response data structures | 📊 Data structures |
| [API Examples](API_EXAMPLES.md) | Code examples & use cases | 💡 Practical examples |

## 🚀 API Overview

### **REST API**

- **Base URL**: `https://api.tripsage.ai/v1`
- **Authentication**: API Key, JWT, OAuth 2.0
- **Format**: JSON request/response
- **Rate Limiting**: 1000 requests/hour (standard tier)
- **Versioning**: URL-based versioning (`/v1/`, `/v2/`)

### **WebSocket API**

- **Endpoint**: `wss://api.tripsage.ai/ws`
- **Authentication**: JWT token or API key
- **Features**: Real-time updates, agent communication
- **Protocols**: JSON-RPC 2.0 over WebSocket

### **GraphQL API**

- **Endpoint**: `https://api.tripsage.ai/graphql`
- **Schema**: Auto-generated from Pydantic models
- **Features**: Flexible queries, real-time subscriptions
- **Tools**: GraphQL Playground available

## 🔌 Core API Endpoints

### **Travel Planning**

```plaintext
GET    /api/v1/destinations/search      # Search destinations
GET    /api/v1/flights/search          # Search flights
GET    /api/v1/accommodations/search   # Search accommodations
POST   /api/v1/trips                   # Create trip plan
GET    /api/v1/trips/{trip_id}         # Get trip details
PUT    /api/v1/trips/{trip_id}         # Update trip plan
```

### **User Management**

```plaintext
POST   /api/v1/auth/register           # User registration
POST   /api/v1/auth/login              # User authentication
POST   /api/v1/auth/refresh            # Refresh tokens
GET    /api/v1/users/profile           # Get user profile
PUT    /api/v1/users/profile           # Update user profile
```

### **AI & Memory**

```plaintext
POST   /api/v1/chat/completions        # Chat with AI agents
GET    /api/v1/memory/conversations    # Get conversation history
POST   /api/v1/memory/preferences      # Update user preferences
GET    /api/v1/agents/status           # Get agent status
POST   /api/v1/agents/handoff          # Trigger agent handoff
```

## 📊 Data Models

### **Core Travel Models**

```python
# Trip Model
class Trip(BaseModel):
    trip_id: str
    user_id: str
    title: str
    description: Optional[str]
    start_date: datetime
    end_date: datetime
    destinations: List[Destination]
    flights: List[Flight]
    accommodations: List[Accommodation]
    status: TripStatus

# Flight Model
class Flight(BaseModel):
    flight_id: str
    airline: str
    flight_number: str
    departure: Airport
    arrival: Airport
    departure_time: datetime
    arrival_time: datetime
    price: Money
    booking_class: str
```

### **Authentication Models**

```python
# User Model
class User(BaseModel):
    user_id: str
    email: EmailStr
    profile: UserProfile
    preferences: UserPreferences
    created_at: datetime
    updated_at: datetime

# API Key Model
class APIKey(BaseModel):
    key_id: str
    user_id: str
    name: str
    key_hash: str
    permissions: List[Permission]
    expires_at: Optional[datetime]
```

## 🔒 Authentication

### **API Key Authentication**

```http
GET /api/v1/destinations/search
Authorization: Bearer your-api-key-here
Content-Type: application/json
```

### **JWT Authentication**

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure-password"
}

# Response includes access_token and refresh_token
```

### **OAuth 2.0 Flow**

```plaintext
1. Redirect to: /api/v1/auth/oauth/authorize?provider=google
2. Callback to: /api/v1/auth/oauth/callback
3. Receive JWT tokens in response
```

## ⚡ WebSocket Communication

### **Connection Setup**

```javascript
const ws = new WebSocket('wss://api.tripsage.ai/ws');
ws.onopen = () => {
  // Send authentication
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'your-jwt-token'
  }));
};
```

### **Real-Time Events**

```javascript
// Agent status updates
{
  "type": "agent_status",
  "agent_id": "flight_agent",
  "status": "searching",
  "message": "Searching for flights..."
}

// Trip updates
{
  "type": "trip_update",
  "trip_id": "trip_123",
  "changes": {
    "flights": [...],
    "total_cost": 1250.00
  }
}
```

## 🚨 Error Handling

### **Standard Error Response**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "departure_date",
      "issue": "Date must be in the future"
    },
    "request_id": "req_abc123"
  }
}
```

### **HTTP Status Codes**

- **200**: Success
- **201**: Created
- **400**: Bad Request
- **401**: Unauthorized
- **403**: Forbidden
- **404**: Not Found
- **429**: Rate Limited
- **500**: Internal Server Error

## 📈 Rate Limiting

### **Rate Limit Headers**

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
X-RateLimit-Window: 3600
```

### **Rate Limit Tiers**

- **Free**: 100 requests/hour
- **Standard**: 1,000 requests/hour
- **Premium**: 10,000 requests/hour
- **Enterprise**: Custom limits

## 🔄 Pagination

### **Cursor-Based Pagination**

```json
{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6IjEyMyJ9",
    "prev_cursor": "eyJpZCI6IjEwMSJ9",
    "has_more": true,
    "total_count": 1500
  }
}
```

### **Page-Based Pagination**

```http
GET /api/v1/trips?page=2&size=20&sort=created_at:desc
```

## 🔗 SDK & Libraries

### **Official SDKs**

- **Python**: `pip install tripsage-python`
- **JavaScript/TypeScript**: `npm install tripsage-js`
- **React**: `npm install @tripsage/react`

### **Community Libraries**

- **Go**: `github.com/community/tripsage-go`
- **PHP**: `composer require community/tripsage-php`
- **Ruby**: `gem install tripsage-ruby`

## 📖 Interactive Documentation

### **API Explorer**

- **Swagger UI**: `https://api.tripsage.ai/docs`
- **GraphQL Playground**: `https://api.tripsage.ai/graphql`
- **Postman Collection**: Available in developer portal

### **Code Examples**

- **cURL Examples**: Complete command-line examples
- **Language SDKs**: Examples in Python, JavaScript, etc.
- **Integration Patterns**: Common use case implementations

## 🔗 Related Documentation

### **Implementation Guides**

- **[Getting Started](../01_GETTING_STARTED/README.md)** - Setup and installation
- **[Development Guide](../04_DEVELOPMENT_GUIDE/README.md)** - Developer resources
- **[Features](../05_FEATURES_AND_INTEGRATIONS/README.md)** - Feature documentation

### **Configuration**

- **[Configuration](../07_CONFIGURATION/README.md)** - Settings & environment
- **[Authentication System](../05_FEATURES_AND_INTEGRATIONS/AUTHENTICATION_SYSTEM.md)** - Auth details

### **User Resources**

- **[User Guides](../08_USER_GUIDES/README.md)** - End-user documentation
- **[API Usage Examples](../08_USER_GUIDES/API_USAGE_EXAMPLES.md)** - Developer examples

---

*This API reference provides complete technical documentation for integrating with TripSage's powerful travel planning and AI capabilities.*
