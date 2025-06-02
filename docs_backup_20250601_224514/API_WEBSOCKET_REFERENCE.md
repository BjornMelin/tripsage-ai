# WebSocket API Reference

This document provides a comprehensive API reference for TripSage's WebSocket infrastructure.

## Table of Contents

1. [Connection Endpoints](#connection-endpoints)
2. [Authentication](#authentication)
3. [Event Types](#event-types)
4. [Message Formats](#message-formats)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)
7. [Performance Monitoring](#performance-monitoring)

## Connection Endpoints

### Chat WebSocket

Connect to real-time chat functionality:

```plaintext
WS /ws/chat/{session_id}
```

**Parameters:**

- `session_id` (string): Unique chat session identifier

**Example:**

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/session-123');
```

### Agent Status WebSocket

Connect to real-time agent status updates:

```plaintext
WS /ws/agent-status/{session_id}
```

**Parameters:**

- `session_id` (string): Session identifier for agent tracking

**Example:**

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/agent-status/session-123');
```

## Authentication

All WebSocket connections require JWT authentication.

### Authentication Request

Send immediately after connection establishment:

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "sessionId": "session-123",
  "channels": ["chat:session-123", "agent:user-456"]
}
```

**Fields:**

- `token` (string, required): Valid JWT authentication token
- `sessionId` (string, optional): Session identifier for scoped access
- `channels` (array, optional): Channels to subscribe to

### Authentication Response

Success response:

```json
{
  "success": true,
  "connectionId": "conn-789",
  "userId": "user-456",
  "sessionId": "session-123",
  "availableChannels": ["chat:session-123", "agent:user-456"]
}
```

Error response:

```json
{
  "success": false,
  "error": "Invalid token",
  "code": "AUTH_FAILED",
  "retryAfter": 30
}
```

## Event Types

### Chat Events

#### `chat_message`

Complete chat message from user or assistant.

**Direction:** Bidirectional

**Payload:**

```json
{
  "id": "msg-123",
  "type": "chat_message",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "sessionId": "session-123",
  "payload": {
    "content": "Hello, how can I help you plan your trip?",
    "role": "assistant",
    "messageId": "msg-123",
    "attachments": [
      {
        "id": "att-456",
        "url": "https://example.com/file.pdf",
        "name": "itinerary.pdf",
        "contentType": "application/pdf",
        "size": 1024
      }
    ],
    "toolCalls": [
      {
        "id": "call-789",
        "name": "search_flights",
        "arguments": {"origin": "NYC", "destination": "LAX"},
        "state": "result"
      }
    ]
  }
}
```

#### `chat_message_chunk`

Streaming message chunk for real-time typing effect.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "chunk-123",
  "type": "chat_message_chunk",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "sessionId": "session-123",
  "payload": {
    "messageId": "msg-123",
    "content": "I can help you find",
    "isComplete": false,
    "chunkIndex": 1
  }
}
```

#### `chat_message_complete`

Indicates streaming message is complete.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "complete-123",
  "type": "chat_message_complete", 
  "timestamp": "2025-05-28T01:30:00.000Z",
  "sessionId": "session-123",
  "payload": {
    "messageId": "msg-123",
    "finalContent": "I can help you find the best flights for your trip!",
    "metadata": {
      "processingTime": 1.5,
      "tokenCount": 12
    }
  }
}
```

### Typing Events

#### `chat_typing_start`

User started typing indicator.

**Direction:** Bidirectional

**Payload:**

```json
{
  "id": "typing-start-123",
  "type": "chat_typing_start",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "sessionId": "session-123",
  "payload": {
    "userId": "user-456",
    "username": "John Doe"
  }
}
```

#### `chat_typing_stop`

User stopped typing indicator.

**Direction:** Bidirectional

**Payload:**

```json
{
  "id": "typing-stop-123",
  "type": "chat_typing_stop",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "sessionId": "session-123",
  "payload": {
    "userId": "user-456"
  }
}
```

### Tool Events

#### `tool_call_start`

Agent started executing a tool.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "tool-start-123",
  "type": "tool_call_start",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "sessionId": "session-123",
  "payload": {
    "toolCallId": "call-789",
    "toolName": "search_flights",
    "arguments": {"origin": "NYC", "destination": "LAX"},
    "estimatedDuration": 5.0
  }
}
```

#### `tool_call_progress`

Progress update for long-running tool execution.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "tool-progress-123",
  "type": "tool_call_progress",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "sessionId": "session-123",
  "payload": {
    "toolCallId": "call-789",
    "progress": 0.6,
    "status": "Searching airline APIs...",
    "intermediateResults": {
      "apisCalled": 3,
      "resultsFound": 12
    }
  }
}
```

#### `tool_call_complete`

Tool execution completed successfully.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "tool-complete-123",
  "type": "tool_call_complete",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "sessionId": "session-123",
  "payload": {
    "toolCallId": "call-789",
    "result": {
      "flights": [
        {
          "airline": "American Airlines",
          "price": 299,
          "departure": "2025-06-01T08:00:00Z"
        }
      ]
    },
    "executionTime": 4.2
  }
}
```

#### `tool_call_error`

Tool execution failed with error.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "tool-error-123",
  "type": "tool_call_error",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "sessionId": "session-123",
  "payload": {
    "toolCallId": "call-789",
    "error": "API rate limit exceeded",
    "errorCode": "RATE_LIMITED",
    "retryAfter": 60,
    "fallbackOptions": ["manual_search", "cached_results"]
  }
}
```

### Agent Status Events

#### `agent_status_update`

General agent status update.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "status-123",
  "type": "agent_status_update",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "sessionId": "session-123",
  "payload": {
    "agentId": "agent-travel-planner",
    "isActive": true,
    "currentTask": "Planning your 7-day Europe itinerary",
    "progress": 0.75,
    "statusMessage": "Finalizing hotel recommendations...",
    "estimatedCompletion": "2025-05-28T01:35:00.000Z"
  }
}
```

#### `agent_task_start`

Agent started a new task.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "task-start-123",
  "type": "agent_task_start",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "sessionId": "session-123",
  "payload": {
    "taskId": "task-456",
    "taskName": "search_accommodations",
    "taskDescription": "Finding hotels in Paris for June 1-7",
    "estimatedDuration": 30.0,
    "priority": "high"
  }
}
```

#### `agent_task_progress`

Progress update for ongoing task.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "task-progress-123",
  "type": "agent_task_progress",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "sessionId": "session-123",
  "payload": {
    "taskId": "task-456",
    "progress": 0.4,
    "currentStep": "Analyzing hotel ratings and reviews",
    "stepsCompleted": 2,
    "totalSteps": 5,
    "intermediateResults": {
      "hotelsFound": 23,
      "priceRange": "$89-$450"
    }
  }
}
```

#### `agent_task_complete`

Task completed successfully.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "task-complete-123",
  "type": "agent_task_complete",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "sessionId": "session-123",
  "payload": {
    "taskId": "task-456",
    "result": {
      "recommendations": [
        {
          "name": "Hotel des Invalides",
          "rating": 4.8,
          "price": 185,
          "location": "7th Arrondissement"
        }
      ],
      "totalOptions": 23,
      "processingTime": 28.5
    },
    "nextTask": "booking_confirmation"
  }
}
```

### Connection Events

#### `connection_established`

Connection successfully established and authenticated.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "conn-established-123",
  "type": "connection_established",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "payload": {
    "connectionId": "conn-789",
    "serverVersion": "1.0.0",
    "features": ["message_batching", "compression", "heartbeat"],
    "limits": {
      "maxMessageSize": 1048576,
      "maxConnections": 1000,
      "rateLimitPerMinute": 100
    }
  }
}
```

#### `connection_heartbeat`

Keep-alive heartbeat message.

**Direction:** Bidirectional

**Payload:**

```json
{
  "id": "heartbeat-123",
  "type": "connection_heartbeat",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "payload": {
    "connectionId": "conn-789",
    "serverTime": "2025-05-28T01:30:00.000Z",
    "metrics": {
      "uptime": 3600,
      "messagesSent": 42,
      "messagesReceived": 38
    }
  }
}
```

#### `connection_error`

Connection-level error occurred.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "conn-error-123",
  "type": "connection_error",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "payload": {
    "errorCode": "RATE_LIMITED",
    "message": "Rate limit exceeded. Please slow down.",
    "retryAfter": 60,
    "severity": "warning"
  }
}
```

#### `connection_close`

Connection is being closed.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "conn-close-123",
  "type": "connection_close",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "payload": {
    "reason": "Server maintenance",
    "code": 1001,
    "gracePeriod": 30,
    "reconnectAfter": 120
  }
}
```

### System Events

#### `error`

General error message.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "error-123",
  "type": "error",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "payload": {
    "code": "INVALID_MESSAGE_FORMAT",
    "message": "Message payload is missing required field 'content'",
    "details": {
      "field": "content",
      "expected": "string",
      "received": "undefined"
    },
    "severity": "error"
  }
}
```

#### `notification`

System notification message.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "notification-123",
  "type": "notification",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "payload": {
    "title": "New Feature Available",
    "message": "Real-time flight price alerts are now enabled!",
    "type": "info",
    "actionUrl": "/features/price-alerts",
    "dismissible": true
  }
}
```

#### `system_message`

Important system-wide message.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "system-123",
  "type": "system_message",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "payload": {
    "level": "maintenance",
    "message": "Scheduled maintenance in 15 minutes. Connections will be temporarily unavailable.",
    "scheduledTime": "2025-05-28T02:00:00.000Z",
    "estimatedDuration": 900,
    "affectedServices": ["chat", "agent_status"]
  }
}
```

## Message Formats

### Base Message Structure

All WebSocket messages follow this structure:

```json
{
  "id": "unique-message-id",
  "type": "event_type_name",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "userId": "user-456",
  "sessionId": "session-123", 
  "payload": {
    // Event-specific data
  }
}
```

**Fields:**

- `id` (string, required): Unique message identifier
- `type` (string, required): Event type from enum
- `timestamp` (string, required): ISO 8601 timestamp
- `userId` (string, optional): User identifier
- `sessionId` (string, optional): Session identifier
- `payload` (object, required): Event-specific data

### Batch Messages

For performance optimization, multiple messages can be batched:

```json
{
  "type": "batch",
  "payload": {
    "messages": [
      {
        "id": "msg-1",
        "type": "chat_message",
        "timestamp": "2025-05-28T01:30:00.000Z",
        "payload": { "content": "Hello" }
      },
      {
        "id": "msg-2", 
        "type": "user_typing",
        "timestamp": "2025-05-28T01:30:00.100Z",
        "payload": { "userId": "user-456" }
      }
    ]
  }
}
```

### Channel Subscription

Subscribe to specific channels for targeted message delivery:

```json
{
  "type": "subscribe",
  "payload": {
    "channels": ["chat:session-123", "agent:user-456"],
    "unsubscribeChannels": ["old-channel"]
  }
}
```

**Response:**

```json
{
  "type": "subscription_update",
  "payload": {
    "subscribedChannels": ["chat:session-123", "agent:user-456"],
    "success": true
  }
}
```

## Error Handling

### Error Codes

| Code | Description | Action |
|------|-------------|--------|
| `AUTH_FAILED` | Authentication failed | Re-authenticate |
| `INVALID_TOKEN` | JWT token invalid | Refresh token |
| `TOKEN_EXPIRED` | JWT token expired | Refresh token |
| `RATE_LIMITED` | Rate limit exceeded | Slow down requests |
| `INVALID_MESSAGE_FORMAT` | Message format error | Fix message structure |
| `CHANNEL_NOT_FOUND` | Channel doesn't exist | Check channel name |
| `PERMISSION_DENIED` | Insufficient permissions | Check user access |
| `CONNECTION_LIMIT_EXCEEDED` | Too many connections | Close unused connections |
| `MESSAGE_TOO_LARGE` | Message exceeds size limit | Reduce message size |
| `SERVER_ERROR` | Internal server error | Retry later |

### Error Response Format

```json
{
  "id": "error-123",
  "type": "error",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "payload": {
    "code": "AUTH_FAILED",
    "message": "Authentication token is invalid",
    "details": {
      "reason": "Token signature verification failed",
      "hint": "Please obtain a new token"
    },
    "retryAfter": 0,
    "severity": "error"
  }
}
```

### Connection Close Codes

| Code | Description | Reconnect |
|------|-------------|-----------|
| 1000 | Normal closure | No |
| 1001 | Going away | Yes |
| 1006 | Abnormal closure | Yes |
| 1008 | Policy violation | No |
| 1011 | Server error | Yes |
| 3000 | Authentication failed | No |
| 3001 | Rate limited | Yes (after delay) |

## Rate Limiting

### Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| Connection establishment | 10/min | Per IP |
| Message sending | 100/min | Per user |
| Authentication attempts | 5/min | Per IP |
| Channel subscriptions | 20/min | Per user |

### Rate Limit Headers

Rate limit information is provided in error responses:

```json
{
  "type": "error",
  "payload": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded",
    "retryAfter": 60,
    "limits": {
      "current": 101,
      "limit": 100,
      "window": 60,
      "reset": "2025-05-28T01:31:00.000Z"
    }
  }
}
```

## Performance Monitoring

### Metrics Available

#### Connection Metrics

```json
{
  "type": "performance_metrics",
  "payload": {
    "connections": {
      "active": 256,
      "peak": 512,
      "total": 1024
    },
    "messages": {
      "sent": 10000,
      "received": 9500,
      "perSecond": 42.5
    },
    "performance": {
      "averageLatency": 25.5,
      "maxLatency": 150,
      "uptime": 86400
    }
  }
}
```

#### Client Metrics

```javascript
// Get client performance metrics
const metrics = client.getPerformanceMetrics();
console.log(metrics);
// {
//   messagesSent: 45,
//   messagesReceived: 38, 
//   bytesSent: 12543,
//   bytesReceived: 9876,
//   connectionDuration: 30000,
//   messagesPerSecond: 2.77,
//   averageMessageSize: 278.7,
//   queuedMessages: 0,
//   isHighFrequency: false
// }
```

### Health Checks

#### Connection Health

```json
{
  "type": "connection_health",
  "payload": {
    "status": "healthy",
    "latency": 25,
    "lastHeartbeat": "2025-05-28T01:30:00.000Z",
    "messagesInQueue": 0,
    "connectionStable": true
  }
}
```

#### Server Health

```json
{
  "type": "server_health", 
  "payload": {
    "status": "operational",
    "version": "1.0.0",
    "uptime": 86400,
    "connections": 256,
    "memoryUsage": 0.65,
    "cpuUsage": 0.23
  }
}
```

---

*Last updated: 2025-05-28*  
*API Version: 1.0.0*
