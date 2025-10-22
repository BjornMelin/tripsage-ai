# TripSage API Examples & Tutorials

> **Complete Integration Guide**  
> Real-world examples, SDKs, webhooks, and step-by-step tutorials for TripSage API
> **Need quick code snippets?** Check out our [**Quick Reference Examples**](usage-examples.md) for immediate copy-paste solutions.

## Table of Contents

- [Quick Start Examples](#quick-start-examples)
- [Complete Trip Planning Flow](#complete-trip-planning-flow)
- [SDK Examples](#sdk-examples)
- [Webhook Integration](#webhook-integration)
- [Advanced Use Cases](#advanced-use-cases)
- [Error Handling Examples](#error-handling-examples)
- [Performance Optimization](#performance-optimization)
- [Testing & Development](#testing--development)

---

## Quick Start Examples

### 1. Authentication & Basic Trip Creation

```bash
# 1. Login to get JWT token
curl -X POST "https://api.tripsage.ai/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password"
  }'

# Response: Save the access_token
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "user": { ... }
# }

# 2. Create a simple trip
curl -X POST "https://api.tripsage.ai/api/trips" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Weekend in Paris",
    "start_date": "2025-06-01",
    "end_date": "2025-06-03",
    "destinations": [
      {
        "name": "Paris",
        "country": "France",
        "coordinates": {
          "latitude": 48.8566,
          "longitude": 2.3522
        }
      }
    ]
  }'
```

### 2. Flight Search

```bash
curl -X POST "https://api.tripsage.ai/api/flights/search" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "JFK",
    "destination": "CDG",
    "departure_date": "2025-06-01",
    "return_date": "2025-06-03",
    "passengers": {
      "adults": 1
    },
    "cabin_class": "economy"
  }'
```

### 3. Hotel Search

```bash
curl -X POST "https://api.tripsage.ai/api/accommodations/search" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Paris, France",
    "check_in": "2025-06-01",
    "check_out": "2025-06-03",
    "guests": {
      "adults": 1,
      "rooms": 1
    },
    "filters": {
      "price_range": {
        "max": 200,
        "currency": "USD"
      }
    }
  }'
```

---

## Complete Trip Planning Flow

Here's an example showing the entire trip planning process:

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

class TripSageClient {
  constructor(baseUrl = 'https://api.tripsage.ai') {
    this.baseUrl = baseUrl;
    this.accessToken = null;
  }

  async login(email, password) {
    try {
      const response = await axios.post(`${this.baseUrl}/api/auth/login`, {
        email,
        password
      });
      
      this.accessToken = response.data.access_token;
      return response.data;
    } catch (error) {
      throw new Error(`Login failed: ${error.response?.data?.message || error.message}`);
    }
  }

  getHeaders() {
    return {
      'Authorization': `Bearer ${this.accessToken}`,
      'Content-Type': 'application/json'
    };
  }

  async createTrip(tripData) {
    const response = await axios.post(
      `${this.baseUrl}/api/trips`,
      tripData,
      { headers: this.getHeaders() }
    );
    return response.data;
  }

  async searchFlights(searchParams) {
    const response = await axios.post(
      `${this.baseUrl}/api/flights/search`,
      searchParams,
      { headers: this.getHeaders() }
    );
    return response.data;
  }

  async searchAccommodations(searchParams) {
    const response = await axios.post(
      `${this.baseUrl}/api/accommodations/search`,
      searchParams,
      { headers: this.getHeaders() }
    );
    return response.data;
  }

  async chatWithAI(message, sessionId, context = {}) {
    const response = await axios.post(
      `${this.baseUrl}/api/chat/message`,
      {
        message,
        session_id: sessionId,
        context
      },
      { headers: this.getHeaders() }
    );
    return response.data;
  }
}

// Complete trip planning example
async function planCompleteTrip() {
  const client = new TripSageClient();
  
  try {
    // 1. Authenticate
    console.log('🔐 Authenticating...');
    await client.login('user@example.com', 'password');
    console.log('✅ Authenticated successfully');

    // 2. Create trip
    console.log('🗺️ Creating trip...');
    const trip = await client.createTrip({
      title: 'Japan Adventure',
      description: 'Cherry blossom season exploration',
      start_date: '2025-04-01',
      end_date: '2025-04-08',
      destinations: [
        {
          name: 'Tokyo',
          country: 'Japan',
          coordinates: {
            latitude: 35.6762,
            longitude: 139.6503
          }
        }
      ],
      preferences: {
        budget: {
          total: 3000,
          currency: 'USD'
        },
        interests: ['culture', 'food', 'nature']
      }
    });
    console.log('✅ Trip created:', trip.id);

    // 3. Search flights
    console.log('✈️ Searching flights...');
    const flights = await client.searchFlights({
      origin: 'JFK',
      destination: 'NRT',
      departure_date: '2025-04-01',
      return_date: '2025-04-08',
      passengers: { adults: 1 },
      cabin_class: 'economy',
      filters: {
        max_price: 1500,
        max_stops: 1
      }
    });
    console.log(`✅ Found ${flights.data.length} flights`);

    // 4. Search accommodations
    console.log('🏨 Searching hotels...');
    const hotels = await client.searchAccommodations({
      location: 'Tokyo, Japan',
      check_in: '2025-04-01',
      check_out: '2025-04-08',
      guests: { adults: 1, rooms: 1 },
      filters: {
        price_range: { max: 200, currency: 'USD' },
        amenities: ['wifi', 'breakfast']
      }
    });
    console.log(`✅ Found ${hotels.data.length} hotels`);

    // 5. Get AI recommendations
    console.log('🤖 Getting AI recommendations...');
    const aiResponse = await client.chatWithAI(
      'What are the must-see attractions in Tokyo during cherry blossom season?',
      'session_123',
      { trip_id: trip.id }
    );
    console.log('✅ AI recommendations:', aiResponse.content);

    // 6. Display summary
    console.log('\n📋 Trip Planning Summary:');
    console.log(`Trip: ${trip.title}`);
    console.log(`Dates: ${trip.start_date} to ${trip.end_date}`);
    console.log(`Flights: ${flights.data.length} options found`);
    console.log(`Hotels: ${hotels.data.length} options found`);
    console.log(`Budget: $${trip.preferences.budget.total}`);

    return {
      trip,
      flights: flights.data,
      hotels: hotels.data,
      recommendations: aiResponse.content
    };

  } catch (error) {
    console.error('❌ Error:', error.message);
    throw error;
  }
}

// Run the example
planCompleteTrip()
  .then(result => {
    console.log('🎉 Trip planning completed successfully!');
  })
  .catch(error => {
    console.error('💥 Trip planning failed:', error.message);
  });
```

---

## SDK Examples

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

// Create a trip with TypeScript types
interface TripPreferences {
  budget: {
    total: number;
    currency: string;
  };
  interests: string[];
}

const tripData = {
  title: 'European Adventure',
  startDate: '2025-06-01',
  endDate: '2025-06-14',
  destinations: [
    { name: 'Paris', country: 'France' },
    { name: 'Rome', country: 'Italy' }
  ],
  preferences: {
    budget: { total: 5000, currency: 'USD' },
    interests: ['culture', 'history', 'food']
  } as TripPreferences
};

const trip = await client.trips.create(tripData);

// Search flights with filters
const flights = await client.flights.search({
  origin: 'JFK',
  destination: 'CDG',
  departureDate: '2025-06-01',
  passengers: { adults: 2 },
  filters: {
    maxPrice: 2000,
    airlines: ['AF', 'DL'],
    maxStops: 1
  }
});

// Real-time chat with AI
const chatSession = client.chat.createSession();
const response = await chatSession.sendMessage(
  'Plan a romantic itinerary for Paris',
  { tripId: trip.id }
);
```

### Python SDK

```bash
pip install tripsage-python
```

```python
from tripsage import TripSageClient
from datetime import datetime, timedelta

client = TripSageClient(
    api_key='ts_live_1234567890abcdef',
    base_url='https://api.tripsage.ai'
)

# Create trip with error handling
try:
    trip = client.trips.create({
        'title': 'Asian Adventure',
        'start_date': '2025-05-01',
        'end_date': '2025-05-15',
        'destinations': [
            {'name': 'Tokyo', 'country': 'Japan'},
            {'name': 'Seoul', 'country': 'South Korea'}
        ],
        'preferences': {
            'budget': {'total': 4000, 'currency': 'USD'},
            'interests': ['technology', 'food', 'culture']
        }
    })
    print(f"Trip created: {trip['id']}")
    
except TripSageError as e:
    print(f"Error creating trip: {e.message}")
    if e.code == 'VALIDATION_ERROR':
        for error in e.details.get('errors', []):
            print(f"  - {error['field']}: {error['message']}")

# Async flight search
import asyncio

async def search_flights_async():
    flights = await client.flights.search_async({
        'origin': 'LAX',
        'destination': 'NRT',
        'departure_date': '2025-05-01',
        'return_date': '2025-05-15',
        'passengers': {'adults': 2},
        'cabin_class': 'business'
    })
    
    # Sort by price and duration
    sorted_flights = sorted(
        flights['data'],
        key=lambda f: (f['price']['total'], f['duration_minutes'])
    )
    
    return sorted_flights[:5]  # Top 5 options

# Run async search
best_flights = asyncio.run(search_flights_async())
```

### Go SDK

```bash
go get github.com/tripsage/tripsage-go
```

```go
package main

import (
    "context"
    "fmt"
    "log"
    "time"
    
    "github.com/tripsage/tripsage-go"
)

func main() {
    client := tripsage.NewClient("ts_live_1234567890abcdef")
    ctx := context.Background()
    
    // Create trip with context and timeout
    ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
    defer cancel()
    
    trip, err := client.Trips.Create(ctx, &tripsage.TripCreateRequest{
        Title:     "Australian Road Trip",
        StartDate: "2025-09-01",
        EndDate:   "2025-09-21",
        Destinations: []tripsage.Destination{
            {Name: "Sydney", Country: "Australia"},
            {Name: "Melbourne", Country: "Australia"},
        },
        Preferences: &tripsage.TripPreferences{
            Budget: &tripsage.Budget{
                Total:    6000,
                Currency: "USD",
            },
            Interests: []string{"nature", "adventure", "wildlife"},
        },
    })
    
    if err != nil {
        log.Fatalf("Failed to create trip: %v", err)
    }
    
    fmt.Printf("Trip created: %s\n", trip.ID)
    
    // Search accommodations with retry logic
    var accommodations *tripsage.AccommodationSearchResponse
    for attempts := 0; attempts < 3; attempts++ {
        accommodations, err = client.Accommodations.Search(ctx, &tripsage.AccommodationSearchRequest{
            Location: "Sydney, Australia",
            CheckIn:  "2025-09-01",
            CheckOut: "2025-09-07",
            Guests: &tripsage.GuestInfo{
                Adults: 2,
                Rooms:  1,
            },
            Filters: &tripsage.AccommodationFilters{
                PriceRange: &tripsage.PriceRange{
                    Max:      300,
                    Currency: "USD",
                },
                PropertyTypes: []string{"hotel", "apartment"},
                Amenities:     []string{"wifi", "pool", "gym"},
            },
        })
        
        if err == nil {
            break
        }
        
        if attempts == 2 {
            log.Fatalf("Failed to search accommodations after 3 attempts: %v", err)
        }
        
        time.Sleep(time.Duration(attempts+1) * time.Second)
    }
    
    fmt.Printf("Found %d accommodations\n", len(accommodations.Data))
}
```

---

## Webhook Integration

### Setting Up Webhooks

```javascript
// Configure webhook endpoint
const webhookConfig = {
  url: 'https://your-app.com/webhooks/tripsage',
  events: [
    'trip.created',
    'trip.updated',
    'flight.price_changed',
    'collaboration.added'
  ],
  secret: 'webhook_secret_key_12345'
};

const webhook = await client.webhooks.create(webhookConfig);
console.log('Webhook created:', webhook.id);
```

### Webhook Handler Example (Express.js)

```javascript
const express = require('express');
const crypto = require('crypto');
const app = express();

app.use(express.raw({ type: 'application/json' }));

// Webhook signature verification
function verifyWebhookSignature(payload, signature, secret) {
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');
  
  return crypto.timingSafeEqual(
    Buffer.from(signature, 'hex'),
    Buffer.from(expectedSignature, 'hex')
  );
}

app.post('/webhooks/tripsage', (req, res) => {
  const signature = req.headers['x-tripsage-signature'];
  const payload = req.body;
  
  // Verify webhook signature
  if (!verifyWebhookSignature(payload, signature, 'webhook_secret_key_12345')) {
    return res.status(401).send('Invalid signature');
  }
  
  const event = JSON.parse(payload);
  
  // Handle different event types
  switch (event.type) {
    case 'trip.created':
      handleTripCreated(event.data);
      break;
      
    case 'trip.updated':
      handleTripUpdated(event.data);
      break;
      
    case 'flight.price_changed':
      handleFlightPriceChange(event.data);
      break;
      
    case 'collaboration.added':
      handleCollaborationAdded(event.data);
      break;
      
    default:
      console.log('Unknown event type:', event.type);
  }
  
  res.status(200).send('OK');
});

function handleTripCreated(data) {
  console.log('New trip created:', data.trip_id);
  
  // Send welcome email
  sendWelcomeEmail(data.user_id, data.trip_id);
  
  // Start automated recommendations
  triggerRecommendationEngine(data.trip_id);
}

function handleFlightPriceChange(data) {
  console.log('Flight price changed:', data);
  
  if (data.price_change.percentage < -10) {
    // Price dropped by more than 10%
    sendPriceAlertEmail(data.user_id, data.flight_id, data.price_change);
  }
}

app.listen(3000, () => {
  console.log('Webhook server listening on port 3000');
});
```

---

## Advanced Use Cases

### 1. Multi-City Trip Planning

```javascript
async function planMultiCityTrip() {
  const cities = ['Paris', 'Rome', 'Barcelona', 'Amsterdam'];
  const startDate = '2025-07-01';
  const totalDays = 14;
  const daysPerCity = Math.floor(totalDays / cities.length);
  
  // Create main trip
  const trip = await client.trips.create({
    title: 'European Multi-City Adventure',
    start_date: startDate,
    end_date: addDays(startDate, totalDays),
    destinations: cities.map((city, index) => ({
      name: city,
      country: getCountryForCity(city),
      arrival_date: addDays(startDate, index * daysPerCity),
      departure_date: addDays(startDate, (index + 1) * daysPerCity)
    }))
  });
  
  // Search flights for each leg
  const flightLegs = [];
  for (let i = 0; i < cities.length; i++) {
    const origin = i === 0 ? 'JFK' : getAirportCode(cities[i - 1]);
    const destination = getAirportCode(cities[i]);
    const departureDate = addDays(startDate, i * daysPerCity);
    
    const flights = await client.flights.search({
      origin,
      destination,
      departure_date: departureDate,
      passengers: { adults: 1 },
      trip_type: 'one_way'
    });
    
    flightLegs.push({
      leg: i + 1,
      route: `${origin} → ${destination}`,
      flights: flights.data.slice(0, 3) // Top 3 options
    });
  }
  
  // Return flight
  const returnFlights = await client.flights.search({
    origin: getAirportCode(cities[cities.length - 1]),
    destination: 'JFK',
    departure_date: addDays(startDate, totalDays),
    passengers: { adults: 1 },
    trip_type: 'one_way'
  });
  
  return {
    trip,
    flightLegs,
    returnFlights: returnFlights.data.slice(0, 3)
  };
}
```

### 2. Group Trip Coordination

```javascript
async function coordinateGroupTrip() {
  // Create trip as organizer
  const trip = await client.trips.create({
    title: 'Friends Reunion in Bali',
    start_date: '2025-08-15',
    end_date: '2025-08-22',
    destinations: [{ name: 'Bali', country: 'Indonesia' }]
  });
  
  // Invite collaborators
  const collaborators = [
    'friend1@example.com',
    'friend2@example.com',
    'friend3@example.com'
  ];
  
  for (const email of collaborators) {
    await client.trips.inviteCollaborator(trip.id, {
      email,
      role: 'editor',
      message: 'Join our Bali adventure planning!'
    });
  }
  
  // Create shared chat session
  const chatSession = await client.chat.createSession({
    trip_id: trip.id,
    type: 'group',
    participants: collaborators
  });
  
  // Set up group preferences voting
  const preferences = await client.trips.createPreferencesVoting(trip.id, {
    categories: ['accommodation_type', 'budget_range', 'activities'],
    voting_deadline: '2025-06-01T23:59:59Z'
  });
  
  return {
    trip,
    chatSession,
    preferences
  };
}
```

### 3. Real-time Price Monitoring

```javascript
class FlightPriceMonitor {
  constructor(client) {
    this.client = client;
    this.monitors = new Map();
  }
  
  async startMonitoring(searchParams, options = {}) {
    const monitorId = generateId();
    const {
      checkInterval = 3600000, // 1 hour
      priceThreshold = 0.1, // 10% change
      maxDuration = 7 * 24 * 3600000 // 7 days
    } = options;
    
    const monitor = {
      id: monitorId,
      searchParams,
      lastPrice: null,
      checkInterval,
      priceThreshold,
      startTime: Date.now(),
      maxDuration
    };
    
    this.monitors.set(monitorId, monitor);
    this.scheduleCheck(monitorId);
    
    return monitorId;
  }
  
  async scheduleCheck(monitorId) {
    const monitor = this.monitors.get(monitorId);
    if (!monitor) return;
    
    // Check if monitoring period expired
    if (Date.now() - monitor.startTime > monitor.maxDuration) {
      this.stopMonitoring(monitorId);
      return;
    }
    
    try {
      const flights = await this.client.flights.search(monitor.searchParams);
      const bestFlight = flights.data[0]; // Assuming sorted by price
      
      if (bestFlight && monitor.lastPrice) {
        const priceChange = (bestFlight.price.total - monitor.lastPrice) / monitor.lastPrice;
        
        if (Math.abs(priceChange) >= monitor.priceThreshold) {
          await this.notifyPriceChange(monitorId, {
            flight: bestFlight,
            oldPrice: monitor.lastPrice,
            newPrice: bestFlight.price.total,
            changePercentage: priceChange * 100
          });
        }
      }
      
      monitor.lastPrice = bestFlight?.price.total;
      
      // Schedule next check
      setTimeout(() => this.scheduleCheck(monitorId), monitor.checkInterval);
      
    } catch (error) {
      console.error(`Price monitoring error for ${monitorId}:`, error);
      // Retry with exponential backoff
      setTimeout(() => this.scheduleCheck(monitorId), monitor.checkInterval * 2);
    }
  }
  
  async notifyPriceChange(monitorId, changeData) {
    const monitor = this.monitors.get(monitorId);
    console.log(`Price change detected for monitor ${monitorId}:`, changeData);
    
    // Send notification via webhook or email
    await this.client.notifications.send({
      type: 'flight_price_change',
      data: changeData,
      monitor_id: monitorId
    });
  }
  
  stopMonitoring(monitorId) {
    this.monitors.delete(monitorId);
    console.log(`Stopped monitoring ${monitorId}`);
  }
}

// Usage
const monitor = new FlightPriceMonitor(client);
const monitorId = await monitor.startMonitoring({
  origin: 'JFK',
  destination: 'LHR',
  departure_date: '2025-07-15',
  passengers: { adults: 2 }
}, {
  checkInterval: 1800000, // 30 minutes
  priceThreshold: 0.05 // 5% change
});
```

---

## Error Handling Examples

### Error Handling

```javascript
class TripSageErrorHandler {
  static async withRetry(operation, maxRetries = 3, baseDelay = 1000) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        if (attempt === maxRetries) {
          throw error;
        }
        
        // Exponential backoff for retryable errors
        if (this.isRetryableError(error)) {
          const delay = baseDelay * Math.pow(2, attempt - 1);
          await this.sleep(delay);
          continue;
        }
        
        throw error;
      }
    }
  }
  
  static isRetryableError(error) {
    const retryableCodes = [
      'RATE_LIMIT_EXCEEDED',
      'EXTERNAL_SERVICE_TIMEOUT',
      'TEMPORARY_SERVICE_UNAVAILABLE'
    ];
    
    const retryableStatuses = [429, 502, 503, 504];
    
    return (
      retryableCodes.includes(error.code) ||
      retryableStatuses.includes(error.status)
    );
  }
  
  static async handleApiError(error, context = {}) {
    const errorInfo = {
      message: error.message,
      code: error.code,
      status: error.status,
      context,
      timestamp: new Date().toISOString()
    };
    
    switch (error.code) {
      case 'VALIDATION_ERROR':
        return this.handleValidationError(error, context);
        
      case 'AUTHENTICATION_ERROR':
        return this.handleAuthError(error, context);
        
      case 'RATE_LIMIT_EXCEEDED':
        return this.handleRateLimitError(error, context);
        
      case 'EXTERNAL_SERVICE_ERROR':
        return this.handleExternalServiceError(error, context);
        
      default:
        console.error('Unhandled API error:', errorInfo);
        throw error;
    }
  }
  
  static handleValidationError(error, context) {
    const validationErrors = error.details?.errors || [];
    const fieldErrors = {};
    
    validationErrors.forEach(err => {
      fieldErrors[err.field] = err.message;
    });
    
    return {
      type: 'validation',
      message: 'Please correct the following errors:',
      fieldErrors,
      canRetry: false
    };
  }
  
  static async handleAuthError(error, context) {
    if (error.code === 'TOKEN_EXPIRED') {
      // Attempt token refresh
      try {
        await context.client?.refreshToken();
        return { type: 'auth', message: 'Token refreshed, please retry', canRetry: true };
      } catch (refreshError) {
        return { type: 'auth', message: 'Please log in again', canRetry: false };
      }
    }
    
    return { type: 'auth', message: 'Authentication failed', canRetry: false };
  }
  
  static handleRateLimitError(error, context) {
    const retryAfter = error.details?.retry_after || 60;
    
    return {
      type: 'rate_limit',
      message: `Rate limit exceeded. Retry after ${retryAfter} seconds`,
      retryAfter,
      canRetry: true
    };
  }
  
  static sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Usage example
async function robustFlightSearch(searchParams) {
  try {
    return await TripSageErrorHandler.withRetry(async () => {
      return await client.flights.search(searchParams);
    });
  } catch (error) {
    const handled = await TripSageErrorHandler.handleApiError(error, { client });
    
    if (handled.canRetry) {
      console.log('Retrying after error:', handled.message);
      if (handled.retryAfter) {
        await TripSageErrorHandler.sleep(handled.retryAfter * 1000);
      }
      return await client.flights.search(searchParams);
    }
    
    throw new Error(handled.message);
  }
}
```

---

## Performance Optimization

### Caching Strategy

```javascript
class TripSageCache {
  constructor(ttl = 300000) { // 5 minutes default TTL
    this.cache = new Map();
    this.ttl = ttl;
  }
  
  generateKey(method, params) {
    return `${method}:${JSON.stringify(params)}`;
  }
  
  get(key) {
    const item = this.cache.get(key);
    if (!item) return null;
    
    if (Date.now() > item.expiry) {
      this.cache.delete(key);
      return null;
    }
    
    return item.data;
  }
  
  set(key, data, customTtl = null) {
    const ttl = customTtl || this.ttl;
    this.cache.set(key, {
      data,
      expiry: Date.now() + ttl
    });
  }
  
  async cachedRequest(method, params, requestFn, customTtl = null) {
    const key = this.generateKey(method, params);
    const cached = this.get(key);
    
    if (cached) {
      return cached;
    }
    
    const result = await requestFn();
    this.set(key, result, customTtl);
    return result;
  }
}

// Usage with caching
const cache = new TripSageCache();

async function searchFlightsWithCache(searchParams) {
  return await cache.cachedRequest(
    'flights.search',
    searchParams,
    () => client.flights.search(searchParams),
    600000 // 10 minutes for flight searches
  );
}
```

### Batch Operations

```javascript
class BatchProcessor {
  constructor(client, batchSize = 10, delay = 100) {
    this.client = client;
    this.batchSize = batchSize;
    this.delay = delay;
  }
  
  async processBatch(items, processor) {
    const results = [];
    
    for (let i = 0; i < items.length; i += this.batchSize) {
      const batch = items.slice(i, i + this.batchSize);
      
      const batchPromises = batch.map(async (item, index) => {
        try {
          return await processor(item, i + index);
        } catch (error) {
          console.error(`Batch item ${i + index} failed:`, error);
          return { error: error.message, item };
        }
      });
      
      const batchResults = await Promise.all(batchPromises);
      results.push(...batchResults);
      
      // Add delay between batches to avoid rate limiting
      if (i + this.batchSize < items.length) {
        await new Promise(resolve => setTimeout(resolve, this.delay));
      }
    }
    
    return results;
  }
}

// Batch hotel search for multiple cities
async function searchHotelsForCities(cities, searchParams) {
  const processor = new BatchProcessor(client);
  
  return await processor.processBatch(cities, async (city) => {
    const hotelSearch = {
      ...searchParams,
      location: `${city.name}, ${city.country}`
    };
    
    const results = await client.accommodations.search(hotelSearch);
    return {
      city: city.name,
      hotels: results.data.slice(0, 5) // Top 5 per city
    };
  });
}
```

---

## Testing & Development

### Unit Testing Example

```javascript
const { TripSageClient } = require('@tripsage/sdk');
const nock = require('nock');

describe('TripSage API Integration', () => {
  let client;
  
  beforeEach(() => {
    client = new TripSageClient({
      apiKey: 'test_key',
      baseUrl: 'https://api.test.tripsage.ai'
    });
  });
  
  afterEach(() => {
    nock.cleanAll();
  });
  
  test('should create trip successfully', async () => {
    const tripData = {
      title: 'Test Trip',
      start_date: '2025-06-01',
      end_date: '2025-06-03',
      destinations: [{ name: 'Paris', country: 'France' }]
    };
    
    const expectedResponse = {
      id: 'trip_123',
      ...tripData,
      status: 'planning',
      created_at: '2025-01-15T10:30:00Z'
    };
    
    nock('https://api.test.tripsage.ai')
      .post('/api/trips', tripData)
      .reply(201, expectedResponse);
    
    const result = await client.trips.create(tripData);
    
    expect(result.id).toBe('trip_123');
    expect(result.title).toBe('Test Trip');
    expect(result.status).toBe('planning');
  });
  
  test('should handle validation errors', async () => {
    const invalidTripData = {
      title: '', // Invalid: empty title
      start_date: '2024-01-01', // Invalid: past date
      destinations: [] // Invalid: no destinations
    };
    
    nock('https://api.test.tripsage.ai')
      .post('/api/trips')
      .reply(422, {
        error: true,
        code: 'VALIDATION_ERROR',
        errors: [
          { field: 'title', message: 'Title is required' },
          { field: 'start_date', message: 'Start date must be in the future' },
          { field: 'destinations', message: 'At least one destination is required' }
        ]
      });
    
    await expect(client.trips.create(invalidTripData))
      .rejects
      .toThrow('Validation failed');
  });
});
```

### Integration Testing

```javascript
// Integration test with real API (use test environment)
describe('TripSage Integration Tests', () => {
  let client;
  let testTrip;
  
  beforeAll(async () => {
    client = new TripSageClient({
      apiKey: process.env.TRIPSAGE_TEST_API_KEY,
      baseUrl: 'https://api.test.tripsage.ai'
    });
  });
  
  afterAll(async () => {
    // Cleanup: delete test trip
    if (testTrip) {
      await client.trips.delete(testTrip.id);
    }
  });
  
  test('complete trip planning flow', async () => {
    // Create trip
    testTrip = await client.trips.create({
      title: 'Integration Test Trip',
      start_date: '2025-12-01',
      end_date: '2025-12-03',
      destinations: [{ name: 'London', country: 'UK' }]
    });
    
    expect(testTrip.id).toBeDefined();
    
    // Search flights
    const flights = await client.flights.search({
      origin: 'JFK',
      destination: 'LHR',
      departure_date: '2025-12-01',
      passengers: { adults: 1 }
    });
    
    expect(flights.data.length).toBeGreaterThan(0);
    
    // Search hotels
    const hotels = await client.accommodations.search({
      location: 'London, UK',
      check_in: '2025-12-01',
      check_out: '2025-12-03',
      guests: { adults: 1, rooms: 1 }
    });
    
    expect(hotels.data.length).toBeGreaterThan(0);
    
    // Update trip with selections
    const updatedTrip = await client.trips.update(testTrip.id, {
      status: 'booked'
    });
    
    expect(updatedTrip.status).toBe('booked');
  }, 30000); // 30 second timeout for integration test
});
```

---

## Development Tools

### API Explorer Script

```javascript
#!/usr/bin/env node

const { TripSageClient } = require('@tripsage/sdk');
const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

const client = new TripSageClient({
  apiKey: process.env.TRIPSAGE_API_KEY,
  baseUrl: process.env.TRIPSAGE_BASE_URL || 'https://api.tripsage.ai'
});

const commands = {
  'search-flights': async (args) => {
    const [origin, destination, date] = args;
    const results = await client.flights.search({
      origin,
      destination,
      departure_date: date,
      passengers: { adults: 1 }
    });
    console.log(`Found ${results.data.length} flights:`);
    results.data.slice(0, 3).forEach((flight, i) => {
      console.log(`${i + 1}. ${flight.airline} ${flight.flight_number} - $${flight.price.total}`);
    });
  },
  
  'create-trip': async (args) => {
    const [title, startDate, endDate, destination] = args;
    const trip = await client.trips.create({
      title,
      start_date: startDate,
      end_date: endDate,
      destinations: [{ name: destination, country: 'Unknown' }]
    });
    console.log(`Created trip: ${trip.id} - ${trip.title}`);
  },
  
  'help': () => {
    console.log('Available commands:');
    console.log('  search-flights <origin> <destination> <date>');
    console.log('  create-trip <title> <start_date> <end_date> <destination>');
    console.log('  help');
    console.log('  exit');
  }
};

async function processCommand(input) {
  const [command, ...args] = input.trim().split(' ');
  
  if (command === 'exit') {
    rl.close();
    return;
  }
  
  if (commands[command]) {
    try {
      await commands[command](args);
    } catch (error) {
      console.error('Error:', error.message);
    }
  } else {
    console.log('Unknown command. Type "help" for available commands.');
  }
}

console.log('TripSage API Explorer');
console.log('Type "help" for available commands or "exit" to quit.');

rl.on('line', processCommand);
```

This guide provides real-world examples for integrating with the TripSage API, from simple requests to complex workflows, error handling, and performance optimization.
