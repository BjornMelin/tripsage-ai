# 🚀 API Getting Started Guide

> **From Zero to First API Call in 5 Minutes**  
> Everything you need to start building with TripSage API

## 📋 Prerequisites

Before you begin, ensure you have:

- **TripSage Account**: Sign up at [app.tripsage.ai](https://app.tripsage.ai)
- **API Key**: Generate from Settings → API Keys
- **HTTP Client**: curl, Postman, or your preferred tool
- **Development Environment**: Your favorite IDE or text editor

## 🔑 Step 1: Get Your API Key

### Generate an API Key

1. **Log in** to [app.tripsage.ai](https://app.tripsage.ai)
2. Navigate to **Settings → API Keys**
3. Click **"Generate New Key"**
4. **Name your key** (e.g., "Development", "Production")
5. **Copy the key** - you won't see it again!

### Secure Your Key

```bash
# Add to your environment variables
export TRIPSAGE_API_KEY="your_api_key_here"

# Or in .env file
TRIPSAGE_API_KEY=your_api_key_here
```

**Security Tips:**

- Never commit API keys to version control
- Use environment variables
- Rotate keys regularly
- Use different keys for dev/prod

## 🎯 Step 2: Make Your First API Call

### Test Connection

```bash
curl https://api.tripsage.ai/v1/health \
  -H "Authorization: Bearer $TRIPSAGE_API_KEY"
```

**Expected Response:**

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.5.0",
    "timestamp": "2025-06-17T10:30:00Z"
  }
}
```

### Your First Trip Search

```bash
curl -X POST https://api.tripsage.ai/v1/trips/search \
  -H "Authorization: Bearer $TRIPSAGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "Paris",
    "duration_days": 5,
    "travelers": 2,
    "budget_usd": 3000
  }'
```

## 🛠️ Step 3: Choose Your Integration Method

### Option A: Direct HTTP (Any Language)

**Python Example:**

```python
import requests

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

response = requests.post(
    "https://api.tripsage.ai/v1/flights/search",
    headers=headers,
    json={
        "origin": "NYC",
        "destination": "LON",
        "departure_date": "2025-07-15",
        "return_date": "2025-07-22"
    }
)

flights = response.json()
```

**JavaScript Example:**

```javascript
const response = await fetch('https://api.tripsage.ai/v1/flights/search', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${apiKey}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    origin: 'NYC',
    destination: 'LON',
    departure_date: '2025-07-15',
    return_date: '2025-07-22'
  })
});

const flights = await response.json();
```

### Option B: Official SDKs (Recommended)

**Python SDK:**

```bash
pip install tripsage
```

```python
from tripsage import TripSageClient

client = TripSageClient(api_key="your_api_key")

# Search flights
flights = client.flights.search(
    origin="NYC",
    destination="LON",
    departure_date="2025-07-15",
    return_date="2025-07-22"
)

# Plan with AI
trip = client.ai.plan_trip(
    prompt="Plan a romantic week in Paris for under $3000"
)
```

**JavaScript/TypeScript SDK:**

```bash
npm install @tripsage/sdk
```

```javascript
import { TripSage } from '@tripsage/sdk';

const client = new TripSage({ apiKey: 'your_api_key' });

// Search flights
const flights = await client.flights.search({
  origin: 'NYC',
  destination: 'LON',
  departureDate: '2025-07-15',
  returnDate: '2025-07-22'
});

// Plan with AI
const trip = await client.ai.planTrip({
  prompt: 'Plan a romantic week in Paris for under $3000'
});
```

## 📊 Step 4: Understanding the API Structure

### Base URL

All API requests use this base URL:

```text
https://api.tripsage.ai/v1
```

### Authentication

Include your API key in the Authorization header:

```text
Authorization: Bearer YOUR_API_KEY
```

### Request Format

- **Content-Type**: `application/json`
- **Accept**: `application/json`
- **Method**: GET, POST, PUT, DELETE
- **Body**: JSON (for POST/PUT)

### Response Format

All responses follow this structure:

**Success Response:**

```json
{
  "success": true,
  "data": {
    // Your requested data
  },
  "meta": {
    "request_id": "req_123abc",
    "timestamp": "2025-06-17T10:30:00Z",
    "took_ms": 245
  }
}
```

**Error Response:**

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid departure date format",
    "details": {
      "field": "departure_date",
      "expected": "YYYY-MM-DD"
    }
  },
  "meta": {
    "request_id": "req_456def",
    "timestamp": "2025-06-17T10:30:00Z"
  }
}
```

## 🎨 Step 5: Common API Patterns

### Searching Resources

**Flights Search:**

```bash
POST /v1/flights/search
{
  "origin": "NYC",
  "destination": "PAR",
  "departure_date": "2025-07-15",
  "passengers": {
    "adults": 2,
    "children": 0
  },
  "cabin_class": "economy",
  "direct_only": false
}
```

**Hotels Search:**

```bash
POST /v1/hotels/search
{
  "location": "Paris, France",
  "check_in": "2025-07-15",
  "check_out": "2025-07-20",
  "guests": 2,
  "rooms": 1,
  "min_rating": 4
}
```

### Creating Resources

**Create Trip:**

```bash
POST /v1/trips
{
  "name": "Paris Summer 2025",
  "start_date": "2025-07-15",
  "end_date": "2025-07-22",
  "travelers": ["user123", "user456"],
  "destinations": ["Paris"],
  "budget": {
    "amount": 3000,
    "currency": "USD"
  }
}
```

### Updating Resources

**Update Trip:**

```bash
PUT /v1/trips/{trip_id}
{
  "name": "Paris & London Summer 2025",
  "destinations": ["Paris", "London"]
}
```

### Deleting Resources

```bash
DELETE /v1/trips/{trip_id}
```

## 🔄 Step 6: Real-Time Features

### WebSocket Connection

For real-time features like chat:

```javascript
const ws = new WebSocket('wss://api.tripsage.ai/v1/chat/stream');

ws.on('open', () => {
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'your_api_key'
  }));
});

ws.on('message', (data) => {
  const message = JSON.parse(data);
  console.log('AI says:', message.content);
});

// Send a message
ws.send(JSON.stringify({
  type: 'message',
  content: 'Plan a weekend in NYC'
}));
```

## 📈 Step 7: Best Practices

### Rate Limiting

Monitor rate limit headers:

```text
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1623456789
```

Handle rate limits gracefully:

```python
if response.status_code == 429:
    retry_after = response.headers.get('Retry-After', 60)
    time.sleep(int(retry_after))
    # Retry the request
```

### Error Handling

```javascript
try {
  const response = await client.flights.search(params);
  // Handle success
} catch (error) {
  if (error.code === 'INVALID_REQUEST') {
    // Handle validation errors
  } else if (error.code === 'RATE_LIMITED') {
    // Handle rate limiting
  } else {
    // Handle other errors
  }
}
```

### Pagination

For endpoints that return lists:

```bash
GET /v1/trips?page=1&per_page=20
```

Response includes pagination info:

```json
{
  "data": [...],
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 145,
      "pages": 8
    }
  }
}
```

## 🧪 Step 8: Testing Your Integration

### Use the Sandbox

Test without real charges:

```bash
# Use sandbox URL
https://sandbox.tripsage.ai/v1

# Same API structure, test data
curl https://sandbox.tripsage.ai/v1/flights/search \
  -H "Authorization: Bearer $TRIPSAGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"origin": "TEST_NYC", "destination": "TEST_LON"}'
```

### Test Scenarios

Common test cases:

- Valid requests → Success responses
- Invalid data → Validation errors
- Missing auth → 401 Unauthorized
- Rate limiting → 429 Too Many Requests
- Server errors → 5xx responses

## 🚀 Next Steps

Now that you've made your first API calls:

1. **Explore Endpoints**: Check our [API Reference](rest-endpoints.md)
2. **Try Examples**: See [Usage Examples](usage-examples.md) for common scenarios
3. **Build Something**: Start with a simple integration
4. **Join Community**: Get help in our [Discord](https://discord.gg/tripsage-dev)

### Quick Project Ideas

**Beginner:**

- Trip cost calculator
- Flight price tracker
- Destination explorer

**Intermediate:**

- Travel expense dashboard
- Itinerary generator
- Group trip planner

**In depth:**

- Full travel booking app
- AI travel assistant bot
- Multi-platform integration

## 🆘 Troubleshooting

### Common Issues

#### 401 Unauthorized

- Check API key is correct
- Ensure "Bearer " prefix
- Verify key hasn't expired

#### 400 Bad Request

- Validate JSON format
- Check required fields
- Verify date formats

#### 429 Rate Limited

- Check rate limit headers
- Implement backoff strategy
- Consider upgrading plan

#### 500 Server Error

- Retry with exponential backoff
- Check status page
- Contact support if persistent

---

**Ready for more?** Dive into our [complete API documentation](rest-endpoints.md) or explore [advanced features](usage-examples.md)!

> Need help? Join our [Developer Discord](https://discord.gg/tripsage-dev) or email [api@tripsage.ai](mailto:api@tripsage.ai)
