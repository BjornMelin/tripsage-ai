# Dashboard Monitoring API

This document describes the comprehensive dashboard monitoring API endpoints that provide real-time insights into system performance, API key usage, and service health.

> **Related Documentation:**
> - [Rate Limiting](../developers/rate-limiting.md) - Enhanced rate limiting implementation
> - [Authentication](authentication.md) - API authentication guide
> - [WebSocket API](websocket-api.md) - Real-time WebSocket connections
> - [Error Codes](error-codes.md) - API error reference
> - [Performance Optimization](../developers/performance-optimization.md) - System performance tuning

## Overview

The Dashboard API provides monitoring and analytics capabilities for:
- System health and performance metrics
- API key usage statistics and analytics
- Real-time monitoring data
- Usage trends and historical analysis
- Alert management and notifications
- Rate limit status and quota information
- Service health monitoring
- User activity tracking

## Authentication

All dashboard endpoints require authenticated access. Only users with appropriate permissions can access monitoring data:

- **User Authentication**: JWT tokens for frontend users
- **Admin Access**: Required for full dashboard functionality
- **Agent Access**: Not permitted for dashboard endpoints

For detailed authentication information, see the [Authentication Guide](authentication.md).

> **Related Documentation:**
> - [Authentication Guide](authentication.md) - Complete authentication setup and usage
> - [Rate Limiting](../developers/rate-limiting.md) - Rate limiting implementation details
> - [WebSocket API](websocket-api.md) - Real-time features and WebSocket connections

## Base URL

```
/api/dashboard
```

## Endpoints

### System Overview

#### GET `/overview`

Get high-level system overview and health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2023-01-01T12:00:00Z",
  "uptime_seconds": 86400,
  "version": "1.0.0",
  "environment": "production",
  "total_requests_24h": 15000,
  "total_errors_24h": 75,
  "success_rate_24h": 0.995,
  "active_users_24h": 150,
  "active_api_keys": 25
}
```

**Status Values:**
- `healthy`: All systems operational
- `degraded`: Some issues detected
- `unhealthy`: Critical issues present
- `maintenance`: System under maintenance

### Service Health

#### GET `/services`

Get health status for all external services.

**Response:**
```json
[
  {
    "service": "openai",
    "status": "healthy",
    "latency_ms": 120.0,
    "last_check": "2023-01-01T12:00:00Z",
    "error_rate": 0.01,
    "uptime_percentage": 99.5,
    "message": "Service operational"
  },
  {
    "service": "weather",
    "status": "degraded",
    "latency_ms": 450.0,
    "last_check": "2023-01-01T12:00:00Z",
    "error_rate": 0.05,
    "uptime_percentage": 95.0,
    "message": "High latency detected"
  }
]
```

### Usage Metrics

#### GET `/metrics`

Get comprehensive usage metrics for specified time period.

**Query Parameters:**
- `time_range_hours` (int, optional): Time range in hours (1-168, default: 24)
- `service` (string, optional): Filter by specific service

**Response:**
```json
{
  "period_start": "2023-01-01T11:00:00Z",
  "period_end": "2023-01-01T12:00:00Z",
  "total_requests": 1000,
  "total_errors": 25,
  "success_rate": 0.975,
  "avg_latency_ms": 150.0,
  "p95_latency_ms": 300.0,
  "p99_latency_ms": 500.0,
  "unique_users": 50,
  "unique_endpoints": 15,
  "top_endpoints": [
    {
      "endpoint": "/api/chat",
      "count": 400
    },
    {
      "endpoint": "/api/flights",
      "count": 300
    }
  ],
  "error_breakdown": {
    "validation_error": 10,
    "rate_limit_error": 8,
    "external_api_error": 7
  }
}
```

### Rate Limits

#### GET `/rate-limits`

Get current rate limit status for API keys.

**Query Parameters:**
- `limit` (int, optional): Maximum number of results (1-100, default: 20)

**Response:**
```json
[
  {
    "key_id": "key_12345",
    "current_usage": 75,
    "limit": 100,
    "remaining": 25,
    "window_minutes": 60,
    "reset_at": "2023-01-01T13:00:00Z",
    "percentage_used": 75.0,
    "is_approaching_limit": false
  }
]
```

### Alert Management

#### GET `/alerts`

Get system alerts and notifications.

**Query Parameters:**
- `severity` (string, optional): Filter by severity (low, medium, high, critical)
- `acknowledged` (boolean, optional): Filter by acknowledgment status
- `limit` (int, optional): Maximum number of results (1-200, default: 50)

**Response:**
```json
[
  {
    "alert_id": "alert_12345",
    "severity": "high",
    "type": "spike",
    "message": "Unusual traffic spike detected",
    "created_at": "2023-01-01T11:30:00Z",
    "key_id": "key_12345",
    "service": "openai",
    "acknowledged": false,
    "details": {
      "spike_ratio": 4.5,
      "threshold": 3.0
    }
  }
]
```

#### POST `/alerts/{alert_id}/acknowledge`

Acknowledge a specific alert.

**Response:**
```json
{
  "success": true,
  "message": "Alert acknowledged successfully",
  "alert_id": "alert_12345",
  "acknowledged_by": "user_123",
  "acknowledged_at": "2023-01-01T12:00:00Z"
}
```

#### DELETE `/alerts/{alert_id}`

Dismiss a specific alert.

**Response:**
```json
{
  "success": true,
  "message": "Alert dismissed successfully",
  "alert_id": "alert_12345",
  "dismissed_by": "user_123",
  "dismissed_at": "2023-01-01T12:00:00Z"
}
```

### User Activity

#### GET `/users/activity`

Get user activity metrics and patterns.

**Query Parameters:**
- `time_range_hours` (int, optional): Time range in hours (1-168, default: 24)
- `limit` (int, optional): Maximum number of results (1-100, default: 20)

**Response:**
```json
[
  {
    "user_id": "user_123",
    "user_type": "user",
    "request_count": 250,
    "error_count": 5,
    "success_rate": 0.98,
    "last_activity": "2023-01-01T11:45:00Z",
    "services_used": ["openai", "weather", "flights"],
    "avg_latency_ms": 125.0
  }
]
```

### Trend Analysis

#### GET `/trends/{metric_type}`

Get time series trend data for specific metrics.

**Path Parameters:**
- `metric_type`: Type of metric (request_count, error_rate, latency, active_users)

**Query Parameters:**
- `time_range_hours` (int, optional): Time range in hours (1-168, default: 24)
- `interval_minutes` (int, optional): Data point interval (5-1440, default: 60)

**Response:**
```json
[
  {
    "timestamp": "2023-01-01T11:00:00Z",
    "value": 150.0,
    "metadata": {
      "requests": 150,
      "errors": 3,
      "success_rate": 0.98
    }
  },
  {
    "timestamp": "2023-01-01T12:00:00Z",
    "value": 180.0,
    "metadata": {
      "requests": 180,
      "errors": 4,
      "success_rate": 0.978
    }
  }
]
```

### Analytics Summary

#### GET `/analytics/summary`

Get comprehensive analytics summary.

**Query Parameters:**
- `time_range_hours` (int, optional): Time range in hours (1-168, default: 24)

**Response:**
```json
{
  "period": {
    "start": "2023-01-01T11:00:00Z",
    "end": "2023-01-01T12:00:00Z",
    "hours": 24
  },
  "performance": {
    "total_requests": 15000,
    "total_errors": 75,
    "success_rate": 0.995,
    "avg_latency_ms": 145.0,
    "p95_latency_ms": 280.0
  },
  "services": {
    "total_services": 4,
    "healthy_services": 3,
    "degraded_services": 1,
    "unhealthy_services": 0,
    "service_breakdown": {
      "openai": "healthy",
      "weather": "healthy",
      "googlemaps": "degraded",
      "duffel": "healthy"
    }
  },
  "usage": {
    "active_api_keys": 25,
    "active_users": 150,
    "usage_by_service": {
      "openai": 8000,
      "weather": 4000,
      "googlemaps": 2000,
      "duffel": 1000
    },
    "top_users": [
      {
        "user_id": "user_123",
        "request_count": 500
      }
    ]
  },
  "alerts": {
    "total_alerts": 3,
    "critical_alerts": 0,
    "high_alerts": 1,
    "unacknowledged_alerts": 2
  },
  "trends": {
    "hourly_usage": [
      {
        "timestamp": "2023-01-01T11:00:00Z",
        "requests": 650,
        "errors": 3,
        "success_rate": 0.995
      }
    ],
    "growth_rate": 0.05,
    "peak_hour": "14:00",
    "lowest_hour": "04:00"
  }
}
```

## Real-time Features

### WebSocket Connection

Connect to real-time dashboard updates:

```
/api/dashboard/realtime/ws/{user_id}
```

**Message Types:**
- `metrics`: Real-time performance metrics
- `alert`: New or updated alerts
- `system_event`: System status changes

**Example WebSocket Message:**
```json
{
  "type": "metrics",
  "data": {
    "timestamp": "2023-01-01T12:00:00Z",
    "requests_per_second": 25.5,
    "errors_per_second": 0.2,
    "success_rate": 0.992,
    "avg_latency_ms": 145.0,
    "active_connections": 12,
    "cache_hit_rate": 0.85,
    "memory_usage_percentage": 65.0
  }
}
```

### Server-Sent Events

Alternative real-time updates via SSE:

```
GET /api/dashboard/realtime/events
```

## Error Responses

### HTTP Status Codes

- `200`: Success
- `400`: Bad Request (invalid parameters)
- `401`: Unauthorized (authentication required)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found (resource doesn't exist)
- `422`: Unprocessable Entity (validation error)
- `500`: Internal Server Error

### Error Response Format

```json
{
  "error": true,
  "message": "Detailed error message",
  "code": "ERROR_CODE",
  "type": "error_type"
}
```

## Rate Limiting

Dashboard endpoints are subject to rate limiting:
- **Standard Users**: 100 requests per minute
- **Admin Users**: 500 requests per minute
- **WebSocket Connections**: Limited to 5 concurrent connections per user

For complete rate limiting configuration and implementation details, see the [Rate Limiting Guide](../developers/rate-limiting.md).

## Data Retention

- **Real-time metrics**: 24 hours
- **Hourly aggregates**: 7 days
- **Daily aggregates**: 30 days
- **Alert history**: 90 days

## Security Considerations

1. **Authentication Required**: All endpoints require valid authentication
2. **Permission Checking**: Access control based on user roles
3. **Data Sanitization**: All output is sanitized to prevent XSS
4. **Rate Limiting**: Prevents abuse and ensures fair usage
5. **Audit Logging**: All access is logged for security monitoring

## Usage Examples

### Monitor System Health

```python
import requests

# Get system overview
response = requests.get(
    "/api/dashboard/overview",
    headers={"Authorization": "Bearer <token>"}
)

if response.json()["status"] != "healthy":
    print("System health issue detected!")
```

### Check Rate Limits

```python
# Get rate limit status
response = requests.get(
    "/api/dashboard/rate-limits",
    headers={"Authorization": "Bearer <token>"}
)

for rate_limit in response.json():
    if rate_limit["percentage_used"] > 80:
        print(f"API key {rate_limit['key_id']} approaching limit")
```

### Real-time Monitoring

```javascript
// Connect to WebSocket for real-time updates
const ws = new WebSocket('ws://api.tripsage.com/api/dashboard/realtime/ws/user_123');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (data.type === 'alert') {
        showAlert(data.data);
    } else if (data.type === 'metrics') {
        updateMetrics(data.data);
    }
};
```

This dashboard API provides comprehensive monitoring capabilities for maintaining system health and performance visibility.

## See Also

- [Error Codes](error-codes.md) - Complete API error reference
- [REST Endpoints](rest-endpoints.md) - Core API endpoints
- [WebSocket Guide](websocket-guide.md) - Real-time communication setup
- [Rate Limiting](../developers/rate-limiting.md) - Rate limiting implementation
- [Performance Optimization](../developers/performance-optimization.md) - System performance guides