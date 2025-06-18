# 🚨 TripSage API Error Codes

> **Complete Error Reference**  
> Comprehensive guide to HTTP status codes, error types, and troubleshooting for TripSage API

## 📋 Table of Contents

- [Error Response Format](#error-response-format)
- [HTTP Status Codes](#http-status-codes)
- [Error Types](#error-types)
- [Validation Errors](#validation-errors)
- [Rate Limiting Errors](#rate-limiting-errors)
- [Authentication Errors](#authentication-errors)
- [External Service Errors](#external-service-errors)
- [Troubleshooting Guide](#troubleshooting-guide)

---

## Error Response Format

All TripSage API errors follow a consistent JSON structure for predictable error handling.

### Standard Error Response

```json
{
  "error": true,
  "message": "Human-readable error description",
  "code": "MACHINE_READABLE_CODE",
  "type": "error_category",
  "details": {
    "field": "specific_field_error",
    "validation_errors": []
  },
  "request_id": "req_abc123",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Error Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `error` | boolean | Always `true` for error responses |
| `message` | string | Human-readable error description |
| `code` | string | Machine-readable error code |
| `type` | string | Error category for programmatic handling |
| `details` | object | Additional error-specific information |
| `request_id` | string | Unique request identifier for support |
| `timestamp` | string | ISO 8601 timestamp of the error |

---

## HTTP Status Codes

### Success Codes (2xx)

| Code | Status | Description | Usage |
|------|--------|-------------|-------|
| `200` | OK | Request completed successfully | GET, PUT, DELETE operations |
| `201` | Created | Resource created successfully | POST operations |
| `202` | Accepted | Request accepted for processing | Async operations |
| `204` | No Content | Request successful, no content returned | DELETE operations |

### Client Error Codes (4xx)

| Code | Status | Description | Common Causes |
|------|--------|-------------|---------------|
| `400` | Bad Request | Invalid request parameters | Malformed JSON, missing required fields |
| `401` | Unauthorized | Missing or invalid authentication | No token, expired token, invalid API key |
| `403` | Forbidden | Insufficient permissions | Wrong scope, account suspended |
| `404` | Not Found | Resource doesn't exist | Invalid trip ID, deleted resource |
| `405` | Method Not Allowed | HTTP method not supported | Using POST on GET-only endpoint |
| `409` | Conflict | Resource conflict | Duplicate trip name, booking conflict |
| `422` | Unprocessable Entity | Validation errors | Invalid date format, business rule violations |
| `429` | Too Many Requests | Rate limit exceeded | API quota exceeded |

### Server Error Codes (5xx)

| Code | Status | Description | Action |
|------|--------|-------------|--------|
| `500` | Internal Server Error | Server-side error | Retry request, contact support |
| `502` | Bad Gateway | Upstream service error | Retry request |
| `503` | Service Unavailable | Service temporarily unavailable | Retry with exponential backoff |
| `504` | Gateway Timeout | Request timeout | Retry request |

---

## 🔧 Quick Error Reference

### Most Common Issues

| Error | Quick Fix | Code Example |
|-------|-----------|--------------|
| `401 Unauthorized` | Check your Authorization header | `curl -H "Authorization: Bearer your_token"` |
| `400 Bad Request` | Validate JSON format | Use `JSON.stringify()` or validate with schema |
| `422 Validation` | Check required fields | Include all required parameters |
| `429 Rate Limited` | Add retry logic | Wait for `Retry-After` header value |
| `500 Server Error` | Retry with backoff | Implement exponential backoff |

---

## Error Types

### Authentication Errors (`authentication`)

| Code | Message | Solution |
|------|---------|----------|
| `INVALID_TOKEN` | Invalid or malformed token | Check token format and validity |
| `TOKEN_EXPIRED` | Token has expired | Refresh token or re-authenticate |
| `INVALID_API_KEY` | Invalid API key | Verify API key is correct |
| `API_KEY_EXPIRED` | API key has expired | Generate new API key |
| `MISSING_AUTHORIZATION` | Authorization header missing | Include Authorization header |

**Example:**

```json
{
  "error": true,
  "message": "Token has expired",
  "code": "TOKEN_EXPIRED",
  "type": "authentication",
  "details": {
    "expired_at": "2025-01-15T09:30:00Z",
    "current_time": "2025-01-15T10:30:00Z"
  }
}
```

### Authorization Errors (`authorization`)

| Code | Message | Solution |
|------|---------|----------|
| `INSUFFICIENT_PERMISSIONS` | Insufficient permissions for this operation | Check API key scopes |
| `ACCOUNT_SUSPENDED` | Account has been suspended | Contact support |
| `RESOURCE_ACCESS_DENIED` | Access denied to this resource | Verify ownership or permissions |
| `PLAN_LIMIT_EXCEEDED` | Plan limit exceeded | Upgrade plan or reduce usage |

### Validation Errors (`validation`)

| Code | Message | Solution |
|------|---------|----------|
| `REQUIRED_FIELD` | Required field is missing | Include all required fields |
| `INVALID_FORMAT` | Field format is invalid | Check field format requirements |
| `INVALID_DATE_RANGE` | Invalid date range | Ensure start date is before end date |
| `INVALID_COORDINATES` | Invalid coordinates | Use valid latitude/longitude |
| `BUDGET_TOO_LOW` | Budget is below minimum | Increase budget amount |

### Rate Limiting Errors (`ratelimit`)

| Code | Message | Solution |
|------|---------|----------|
| `RATE_LIMIT_EXCEEDED` | Rate limit exceeded | Wait and retry |
| `QUOTA_EXCEEDED` | Monthly quota exceeded | Upgrade plan or wait for reset |
| `CONCURRENT_LIMIT_EXCEEDED` | Too many concurrent requests | Reduce concurrent requests |

### External Service Errors (`external`)

| Code | Message | Solution |
|------|---------|----------|
| `FLIGHT_API_UNAVAILABLE` | Flight search service unavailable | Retry later |
| `ACCOMMODATION_API_ERROR` | Accommodation service error | Try different search parameters |
| `PAYMENT_GATEWAY_ERROR` | Payment processing error | Retry payment |
| `WEATHER_API_TIMEOUT` | Weather service timeout | Weather data may be unavailable |

### Internal Errors (`internal`)

| Code | Message | Solution |
|------|---------|----------|
| `DATABASE_ERROR` | Database operation failed | Retry request, contact support |
| `CACHE_ERROR` | Cache operation failed | Request may be slower |
| `AI_SERVICE_ERROR` | AI service unavailable | AI features temporarily unavailable |

---

## 🛠️ Practical Troubleshooting Scenarios

### Scenario 1: "My API calls are failing with 401"

**Common Causes:**

- Missing `Bearer` prefix in Authorization header
- Using expired or invalid JWT token
- API key not properly configured

**Debug Steps:**

```bash
# 1. Check your token format
curl -H "Authorization: Bearer your_token" \
  https://api.tripsage.ai/api/health

# 2. Verify token expiration
echo "your_jwt_token" | cut -d. -f2 | base64 -d | jq .exp

# 3. Get a fresh token
curl -X POST https://api.tripsage.ai/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "password"}'
```

### Scenario 2: "Flight searches return empty results"

**Possible Issues:**

- Invalid airport codes
- Dates in the past
- No availability for selected dates
- External API service down

**Troubleshooting:**

```javascript
// 1. Validate airport codes
const validCodes = await fetch('/api/destinations/search?q=NYC');

// 2. Check date format and future dates
const searchParams = {
  origin: "JFK",
  destination: "LAX",
  departure_date: "2025-12-01", // YYYY-MM-DD format
  return_date: "2025-12-08"
};

// 3. Handle empty results gracefully
const response = await searchFlights(searchParams);
if (response.results.length === 0) {
  // Suggest alternative dates or destinations
  console.log("No flights found. Try different dates or nearby airports.");
}
```

### Scenario 3: "Validation errors on trip creation"

**Example Error Response:**

```json
{
  "error": true,
  "message": "Request validation failed",
  "code": "VALIDATION_ERROR",
  "type": "validation",
  "errors": [
    {
      "field": "start_date",
      "message": "Date must be in the future",
      "type": "value_error.date.past"
    },
    {
      "field": "destinations",
      "message": "At least one destination is required",
      "type": "value_error.list.min_items"
    }
  ]
}
```

**Solution:**

```javascript
function validateTripData(tripData) {
  const errors = [];
  
  // Check dates
  const startDate = new Date(tripData.start_date);
  if (startDate < new Date()) {
    errors.push("Start date must be in the future");
  }
  
  // Check destinations
  if (!tripData.destinations || tripData.destinations.length === 0) {
    errors.push("At least one destination is required");
  }
  
  // Check coordinates if provided
  tripData.destinations.forEach((dest, index) => {
    if (dest.coordinates) {
      const { latitude, longitude } = dest.coordinates;
      if (latitude < -90 || latitude > 90) {
        errors.push(`Invalid latitude for destination ${index + 1}`);
      }
      if (longitude < -180 || longitude > 180) {
        errors.push(`Invalid longitude for destination ${index + 1}`);
      }
    }
  });
  
  return errors;
}
```

### Scenario 4: "WebSocket connection keeps dropping"

**Common Issues:**

- Network connectivity problems
- Authentication token expiration
- Server-side connection limits

**Robust WebSocket Implementation:**

```javascript
class TripSageWebSocket {
  constructor(token) {
    this.token = token;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
  }
  
  connect() {
    this.ws = new WebSocket(`wss://api.tripsage.ai/api/chat/ws?token=${this.token}`);
    
    this.ws.onopen = () => {
      console.log('Connected to TripSage WebSocket');
      this.reconnectAttempts = 0;
    };
    
    this.ws.onclose = (event) => {
      if (event.code === 1006 && this.reconnectAttempts < this.maxReconnectAttempts) {
        // Unexpected close, attempt reconnection
        setTimeout(() => {
          this.reconnectAttempts++;
          this.connect();
        }, this.reconnectDelay * Math.pow(2, this.reconnectAttempts));
      }
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }
}
```

### Scenario 5: "Rate limits being hit unexpectedly"

**Debug Rate Limit Usage:**

```javascript
function monitorRateLimit(response) {
  const limit = response.headers.get('X-RateLimit-Limit');
  const remaining = response.headers.get('X-RateLimit-Remaining');
  const reset = response.headers.get('X-RateLimit-Reset');
  
  console.log(`Rate limit: ${remaining}/${limit} remaining`);
  
  if (remaining < 10) {
    console.warn('Approaching rate limit!');
  }
  
  if (response.status === 429) {
    const retryAfter = response.headers.get('Retry-After');
    console.log(`Rate limited. Retry after ${retryAfter} seconds`);
    return retryAfter;
  }
  
  return null;
}

// Implement request queuing
class RateLimitedClient {
  constructor() {
    this.queue = [];
    this.processing = false;
  }
  
  async request(url, options) {
    return new Promise((resolve, reject) => {
      this.queue.push({ url, options, resolve, reject });
      this.processQueue();
    });
  }
  
  async processQueue() {
    if (this.processing || this.queue.length === 0) return;
    
    this.processing = true;
    
    while (this.queue.length > 0) {
      const { url, options, resolve, reject } = this.queue.shift();
      
      try {
        const response = await fetch(url, options);
        const retryAfter = monitorRateLimit(response);
        
        if (retryAfter) {
          // Re-queue the request
          this.queue.unshift({ url, options, resolve, reject });
          await new Promise(r => setTimeout(r, retryAfter * 1000));
          continue;
        }
        
        resolve(response);
      } catch (error) {
        reject(error);
      }
    }
    
    this.processing = false;
  }
}
```

---

## Validation Errors

For `422` responses, detailed validation errors are provided in the `errors` array:

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
      "type": "value_error",
      "input": "2024-01-01"
    },
    {
      "field": "destinations",
      "message": "At least one destination is required",
      "type": "value_error.missing"
    },
    {
      "field": "budget.total",
      "message": "Budget must be greater than 0",
      "type": "value_error.number.not_gt",
      "input": -100
    }
  ]
}
```

### Common Validation Error Types

| Type | Description | Example |
|------|-------------|---------|
| `value_error.missing` | Required field missing | Missing `title` field |
| `value_error.str.max_length` | String too long | Title exceeds 100 characters |
| `value_error.number.not_gt` | Number not greater than minimum | Budget less than 0 |
| `value_error.date.past` | Date is in the past | Start date before today |
| `value_error.email` | Invalid email format | Malformed email address |
| `value_error.url` | Invalid URL format | Malformed webhook URL |

---

## Rate Limiting Errors

When rate limits are exceeded, the API returns detailed information:

```json
{
  "error": true,
  "message": "Rate limit exceeded. Try again in 60 seconds.",
  "code": "RATE_LIMIT_EXCEEDED",
  "type": "ratelimit",
  "details": {
    "limit": 100,
    "remaining": 0,
    "reset_at": "2025-01-15T11:00:00Z",
    "retry_after": 60,
    "window": 3600
  }
}
```

### Rate Limit Headers

Check these headers to avoid rate limiting:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1642284000
X-RateLimit-Window: 60
```

---

## Authentication Errors

### JWT Token Errors

```json
{
  "error": true,
  "message": "Token signature verification failed",
  "code": "INVALID_TOKEN_SIGNATURE",
  "type": "authentication",
  "details": {
    "token_type": "access_token",
    "issued_at": "2025-01-15T10:00:00Z"
  }
}
```

### API Key Errors

```json
{
  "error": true,
  "message": "API key does not have required permissions",
  "code": "INSUFFICIENT_API_KEY_PERMISSIONS",
  "type": "authorization",
  "details": {
    "required_permissions": ["trips:write"],
    "current_permissions": ["trips:read"]
  }
}
```

---

## External Service Errors

When external services (flights, accommodations) are unavailable:

```json
{
  "error": true,
  "message": "Flight search service is temporarily unavailable",
  "code": "FLIGHT_API_UNAVAILABLE",
  "type": "external",
  "details": {
    "service": "duffel",
    "status": "timeout",
    "retry_after": 300,
    "fallback_available": false
  }
}
```

---

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Authentication Issues

**Problem**: Getting `401 Unauthorized`

```bash
curl -H "Authorization: Bearer invalid_token" \
  "https://api.tripsage.ai/api/trips"
```

**Solutions**:

- Verify token format: `Bearer <token>`
- Check token expiration
- Ensure token has required scopes
- Refresh expired tokens

#### 2. Validation Errors

**Problem**: Getting `422 Unprocessable Entity`

```json
{
  "title": "",
  "start_date": "2024-01-01",
  "destinations": []
}
```

**Solutions**:

- Check required fields
- Validate date formats (ISO 8601)
- Ensure dates are in the future
- Include at least one destination

#### 3. Rate Limiting

**Problem**: Getting `429 Too Many Requests`

**Solutions**:

- Implement exponential backoff
- Check rate limit headers
- Upgrade API plan for higher limits
- Cache responses to reduce requests

#### 4. External Service Failures

**Problem**: Flight searches failing

**Solutions**:

- Retry with exponential backoff
- Check service status page
- Use fallback search parameters
- Implement graceful degradation

### Error Handling Best Practices

#### 1. Implement Retry Logic

```javascript
async function apiRequest(url, options, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, options);
      
      if (response.status === 429) {
        const retryAfter = response.headers.get('Retry-After');
        await sleep(retryAfter * 1000);
        continue;
      }
      
      if (response.status >= 500) {
        await sleep(Math.pow(2, i) * 1000); // Exponential backoff
        continue;
      }
      
      return response;
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await sleep(Math.pow(2, i) * 1000);
    }
  }
}
```

#### 2. Parse Error Responses

```javascript
async function handleApiError(response) {
  const error = await response.json();
  
  switch (error.type) {
    case 'authentication':
      // Refresh token or redirect to login
      break;
    case 'validation':
      // Show field-specific errors to user
      break;
    case 'ratelimit':
      // Implement backoff strategy
      break;
    case 'external':
      // Show service unavailable message
      break;
    default:
      // Generic error handling
  }
}
```

#### 3. Monitor Error Rates

Track error patterns to identify issues:

- High `401` rates → Authentication problems
- High `422` rates → Client validation issues
- High `429` rates → Need rate limit optimization
- High `5xx` rates → Service reliability issues

---

## Support

For persistent errors or questions:

- **Documentation**: Check this error reference
- **Status Page**: [status.tripsage.ai](https://status.tripsage.ai)
- **Support**: <support@tripsage.ai>
- **Discord**: Join our developer community

Include the `request_id` from error responses when contacting support for faster resolution.
