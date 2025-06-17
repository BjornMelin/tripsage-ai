# WebSocket API Reference

This document provides a comprehensive API reference for TripSage's WebSocket infrastructure with real-time collaboration features.

## Table of Contents

1. [Connection Endpoints](#connection-endpoints)
2. [Authentication](#authentication)
3. [Event Types](#event-types)
4. [Real-time Collaboration](#real-time-collaboration)
5. [Optimistic Updates](#optimistic-updates)
6. [Message Formats](#message-formats)
7. [Client Integration](#client-integration)
8. [Error Handling](#error-handling)
9. [Rate Limiting](#rate-limiting)
10. [Performance Monitoring](#performance-monitoring)

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

## Real-time Collaboration

TripSage's WebSocket infrastructure provides comprehensive real-time collaboration features for trip planning, editing, and multi-user coordination.

### Trip Collaboration Events

#### `trip_collaboration_join`

User joins a trip collaboration session.

**Direction:** Bidirectional

**Payload:**

```json
{
  "id": "collab-join-123",
  "type": "trip_collaboration_join",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "payload": {
    "tripId": "trip-456",
    "userId": "user-789",
    "userName": "Jane Doe",
    "avatarUrl": "https://example.com/avatar.jpg",
    "permissionLevel": "editor",
    "sessionId": "session-123"
  }
}
```

#### `trip_collaboration_leave`

User leaves a trip collaboration session.

**Direction:** Bidirectional

**Payload:**

```json
{
  "id": "collab-leave-123",
  "type": "trip_collaboration_leave",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "payload": {
    "tripId": "trip-456",
    "userId": "user-789",
    "sessionId": "session-123"
  }
}
```

#### `trip_field_editing_start`

User starts editing a specific trip field.

**Direction:** Bidirectional

**Payload:**

```json
{
  "id": "field-edit-start-123",
  "type": "trip_field_editing_start",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "payload": {
    "tripId": "trip-456",
    "fieldName": "destination",
    "fieldPath": "trip.destination",
    "userId": "user-789",
    "userName": "Jane Doe",
    "lockId": "lock-abc123"
  }
}
```

#### `trip_field_editing_stop`

User stops editing a specific trip field.

**Direction:** Bidirectional

**Payload:**

```json
{
  "id": "field-edit-stop-123",
  "type": "trip_field_editing_stop",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "payload": {
    "tripId": "trip-456",
    "fieldName": "destination",
    "userId": "user-789",
    "lockId": "lock-abc123"
  }
}
```

#### `trip_update_broadcast`

Real-time trip data update broadcast to all collaborators.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "trip-update-123",
  "type": "trip_update_broadcast",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "payload": {
    "tripId": "trip-456",
    "updatedBy": "user-789",
    "updateType": "field_change",
    "changes": {
      "destination": {
        "oldValue": "Paris, France",
        "newValue": "Rome, Italy",
        "fieldPath": "trip.destination"
      }
    },
    "version": 15,
    "timestamp": "2025-05-28T01:30:00.000Z"
  }
}
```

#### `trip_collaborator_presence`

Real-time presence information for active collaborators.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "presence-123",
  "type": "trip_collaborator_presence",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "payload": {
    "tripId": "trip-456",
    "activeCollaborators": [
      {
        "userId": "user-789",
        "userName": "Jane Doe",
        "avatarUrl": "https://example.com/avatar.jpg",
        "lastSeen": "2025-05-28T01:30:00.000Z",
        "currentField": "budget",
        "isActive": true,
        "permissionLevel": "editor"
      },
      {
        "userId": "user-123",
        "userName": "John Smith",
        "avatarUrl": "https://example.com/avatar2.jpg",
        "lastSeen": "2025-05-28T01:29:45.000Z",
        "currentField": null,
        "isActive": true,
        "permissionLevel": "viewer"
      }
    ]
  }
}
```

#### `trip_conflict_detected`

Conflict detected during concurrent editing.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "conflict-123",
  "type": "trip_conflict_detected",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "payload": {
    "tripId": "trip-456",
    "conflictId": "conflict-789",
    "fieldName": "budget",
    "conflictType": "concurrent_edit",
    "conflictingValues": [
      {
        "userId": "user-123",
        "value": 2000,
        "timestamp": "2025-05-28T01:29:58.000Z"
      },
      {
        "userId": "user-456",
        "value": 2500,
        "timestamp": "2025-05-28T01:30:00.000Z"
      }
    ],
    "resolutionStrategy": "last_write_wins",
    "winningValue": 2500,
    "winningUserId": "user-456"
  }
}
```

#### `trip_permission_change`

Trip collaboration permission levels changed.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "permission-change-123",
  "type": "trip_permission_change",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "payload": {
    "tripId": "trip-456",
    "targetUserId": "user-789",
    "changedBy": "user-123",
    "oldPermission": "viewer",
    "newPermission": "editor",
    "effectiveImmediately": true
  }
}
```

### Collaboration Session Management

#### `collaboration_session_start`

Start a real-time collaboration session.

**Direction:** Client to Server

**Request:**

```json
{
  "type": "collaboration_session_start",
  "payload": {
    "tripId": "trip-456",
    "features": ["real_time_editing", "live_cursors", "typing_indicators"],
    "preferences": {
      "conflictResolution": "manual",
      "autoSave": true,
      "saveInterval": 5000
    }
  }
}
```

**Response:**

```json
{
  "type": "collaboration_session_started",
  "payload": {
    "sessionId": "collab-session-abc123",
    "tripId": "trip-456",
    "activeCollaborators": 3,
    "yourPermissions": {
      "canEdit": true,
      "canInvite": false,
      "canDelete": false
    },
    "features": ["real_time_editing", "live_cursors", "typing_indicators"],
    "serverVersion": 15
  }
}
```

## Optimistic Updates

TripSage implements sophisticated optimistic update patterns for immediate UI responsiveness with conflict resolution.

### Optimistic Update Flow

#### `optimistic_update_start`

Client starts an optimistic update.

**Direction:** Client to Server

**Payload:**

```json
{
  "id": "opt-update-123",
  "type": "optimistic_update_start",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "payload": {
    "updateId": "update-abc123",
    "tripId": "trip-456",
    "fieldName": "destination",
    "optimisticValue": "Rome, Italy",
    "previousValue": "Paris, France",
    "expectedVersion": 14,
    "clientTimestamp": "2025-05-28T01:30:00.000Z"
  }
}
```

#### `optimistic_update_confirmed`

Server confirms optimistic update succeeded.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "opt-confirm-123",
  "type": "optimistic_update_confirmed",
  "timestamp": "2025-05-28T01:30:00.500Z",
  "payload": {
    "updateId": "update-abc123",
    "tripId": "trip-456",
    "fieldName": "destination",
    "confirmedValue": "Rome, Italy",
    "serverVersion": 15,
    "processingTime": 245
  }
}
```

#### `optimistic_update_rejected`

Server rejects optimistic update due to conflict.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "opt-reject-123",
  "type": "optimistic_update_rejected",
  "timestamp": "2025-05-28T01:30:00.500Z",
  "payload": {
    "updateId": "update-abc123",
    "tripId": "trip-456",
    "fieldName": "destination",
    "rejectionReason": "version_conflict",
    "currentServerValue": "Milan, Italy",
    "currentServerVersion": 16,
    "expectedVersion": 14,
    "conflictingUpdate": {
      "userId": "user-789",
      "timestamp": "2025-05-28T01:29:58.000Z"
    },
    "suggestedResolution": "merge_required"
  }
}
```

#### `optimistic_update_rollback`

Client should rollback optimistic update.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "opt-rollback-123",
  "type": "optimistic_update_rollback",
  "timestamp": "2025-05-28T01:30:00.500Z",
  "payload": {
    "updateId": "update-abc123",
    "tripId": "trip-456",
    "fieldName": "destination",
    "rollbackToValue": "Paris, France",
    "rollbackReason": "server_error",
    "canRetry": true,
    "retryAfter": 1000
  }
}
```

### Conflict Resolution

#### `conflict_resolution_required`

Manual conflict resolution required.

**Direction:** Server to Client

**Payload:**

```json
{
  "id": "conflict-res-123",
  "type": "conflict_resolution_required",
  "timestamp": "2025-05-28T01:30:00.000Z",
  "payload": {
    "conflictId": "conflict-789",
    "tripId": "trip-456",
    "fieldName": "budget",
    "options": [
      {
        "id": "option-1",
        "value": 2000,
        "source": "user-123",
        "timestamp": "2025-05-28T01:29:58.000Z",
        "description": "Original budget proposal"
      },
      {
        "id": "option-2",
        "value": 2500,
        "source": "user-456",
        "timestamp": "2025-05-28T01:30:00.000Z",
        "description": "Updated budget with flights"
      },
      {
        "id": "option-3",
        "value": 2250,
        "source": "system",
        "timestamp": "2025-05-28T01:30:00.000Z",
        "description": "Suggested average value"
      }
    ],
    "autoResolveAfter": 30000,
    "defaultOption": "option-2"
  }
}
```

#### `conflict_resolution_submit`

Client submits conflict resolution choice.

**Direction:** Client to Server

**Payload:**

```json
{
  "type": "conflict_resolution_submit",
  "payload": {
    "conflictId": "conflict-789",
    "chosenOptionId": "option-2",
    "customValue": null,
    "reason": "Updated budget includes recent flight price increases"
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

## Client Integration

TripSage provides comprehensive client libraries and integration patterns for seamless WebSocket connectivity.

### React Integration

#### Basic WebSocket Hook

```typescript
import { useWebSocket } from '@/hooks/use-websocket';

function TripCollaboration({ tripId }: { tripId: string }) {
  const { 
    isConnected, 
    sendMessage, 
    lastMessage, 
    connectionState,
    error 
  } = useWebSocket({
    url: `ws://localhost:8000/ws/chat/${tripId}`,
    token: authToken,
    reconnect: true,
    maxReconnectAttempts: 5
  });

  useEffect(() => {
    if (lastMessage?.type === 'trip_update_broadcast') {
      // Handle real-time trip updates
      const { changes, updatedBy } = lastMessage.payload;
      updateTripData(changes);
      showNotification(`Trip updated by ${updatedBy}`);
    }
  }, [lastMessage]);

  const handleTripUpdate = (fieldName: string, value: any) => {
    // Send optimistic update
    sendMessage({
      type: 'optimistic_update_start',
      payload: {
        updateId: generateUpdateId(),
        tripId,
        fieldName,
        optimisticValue: value,
        expectedVersion: currentVersion
      }
    });
  };

  return (
    <div>
      <ConnectionStatus isConnected={isConnected} error={error} />
      <TripEditor onUpdate={handleTripUpdate} />
    </div>
  );
}
```

#### Real-time Collaboration Hook

```typescript
import { useSupabaseRealtime } from '@/hooks/use-supabase-realtime';

function useTripCollaboration(tripId: string) {
  const [activeCollaborators, setActiveCollaborators] = useState([]);
  const [optimisticUpdates, setOptimisticUpdates] = useState({});

  const { isConnected, error } = useSupabaseRealtime({
    table: 'trips',
    filter: `id=eq.${tripId}`,
    onUpdate: (payload) => {
      // Handle real-time trip updates
      handleTripUpdate(payload.new);
    },
    onInsert: (payload) => {
      // Handle new trip data
      handleNewTripData(payload.new);
    }
  });

  const handleOptimisticUpdate = async (field: string, value: any) => {
    const updateId = generateUpdateId();
    
    // Apply optimistic update
    setOptimisticUpdates(prev => ({
      ...prev,
      [field]: { value, status: 'pending', updateId }
    }));

    try {
      await updateTrip({ id: tripId, [field]: value });
      
      // Mark as confirmed
      setOptimisticUpdates(prev => ({
        ...prev,
        [field]: { ...prev[field], status: 'confirmed' }
      }));
    } catch (error) {
      // Rollback optimistic update
      setOptimisticUpdates(prev => {
        const { [field]: removed, ...rest } = prev;
        return rest;
      });
      
      showError(`Failed to update ${field}: ${error.message}`);
    }
  };

  return {
    isConnected,
    error,
    activeCollaborators,
    optimisticUpdates,
    handleOptimisticUpdate
  };
}
```

#### Collaboration Presence Component

```typescript
interface CollaborationPresenceProps {
  tripId: string;
  currentUserId: string;
}

function CollaborationPresence({ tripId, currentUserId }: CollaborationPresenceProps) {
  const [activeUsers, setActiveUsers] = useState<ActiveCollaborator[]>([]);
  const [editingFields, setEditingFields] = useState<Record<string, string>>({});

  const { sendMessage } = useWebSocket({
    url: `ws://localhost:8000/ws/chat/${tripId}`,
    onMessage: (message) => {
      switch (message.type) {
        case 'trip_collaborator_presence':
          setActiveUsers(message.payload.activeCollaborators);
          break;
        
        case 'trip_field_editing_start':
          if (message.payload.userId !== currentUserId) {
            setEditingFields(prev => ({
              ...prev,
              [message.payload.fieldName]: message.payload.userId
            }));
          }
          break;
          
        case 'trip_field_editing_stop':
          setEditingFields(prev => {
            const { [message.payload.fieldName]: removed, ...rest } = prev;
            return rest;
          });
          break;
      }
    }
  });

  const handleFieldFocus = (fieldName: string) => {
    sendMessage({
      type: 'trip_field_editing_start',
      payload: {
        tripId,
        fieldName,
        userId: currentUserId,
        lockId: generateLockId()
      }
    });
  };

  const handleFieldBlur = (fieldName: string) => {
    sendMessage({
      type: 'trip_field_editing_stop',
      payload: {
        tripId,
        fieldName,
        userId: currentUserId
      }
    });
  };

  return (
    <div className="collaboration-presence">
      <div className="active-collaborators">
        {activeUsers.map(user => (
          <CollaboratorAvatar
            key={user.userId}
            user={user}
            isEditing={Object.values(editingFields).includes(user.userId)}
            currentField={user.currentField}
          />
        ))}
      </div>
      
      <div className="editing-indicators">
        {Object.entries(editingFields).map(([field, userId]) => (
          <EditingIndicator
            key={field}
            field={field}
            user={activeUsers.find(u => u.userId === userId)}
          />
        ))}
      </div>
    </div>
  );
}
```

### Vue.js Integration

#### Composition API Hook

```typescript
import { ref, onMounted, onUnmounted } from 'vue';

export function useWebSocketCollaboration(tripId: string) {
  const isConnected = ref(false);
  const activeCollaborators = ref([]);
  const optimisticUpdates = ref({});
  const socket = ref<WebSocket | null>(null);

  const connect = () => {
    socket.value = new WebSocket(`ws://localhost:8000/ws/chat/${tripId}`);
    
    socket.value.onopen = () => {
      isConnected.value = true;
      // Send authentication
      socket.value?.send(JSON.stringify({
        token: authToken,
        sessionId: tripId,
        channels: [`trip:${tripId}`]
      }));
    };

    socket.value.onmessage = (event) => {
      const message = JSON.parse(event.data);
      handleWebSocketMessage(message);
    };

    socket.value.onclose = () => {
      isConnected.value = false;
      // Attempt reconnection
      setTimeout(connect, 1000);
    };
  };

  const handleWebSocketMessage = (message: any) => {
    switch (message.type) {
      case 'trip_collaborator_presence':
        activeCollaborators.value = message.payload.activeCollaborators;
        break;
        
      case 'optimistic_update_confirmed':
        const { updateId, fieldName } = message.payload;
        if (optimisticUpdates.value[fieldName]?.updateId === updateId) {
          optimisticUpdates.value[fieldName].status = 'confirmed';
        }
        break;
        
      case 'optimistic_update_rejected':
        const { updateId: rejectedId, fieldName: rejectedField } = message.payload;
        if (optimisticUpdates.value[rejectedField]?.updateId === rejectedId) {
          delete optimisticUpdates.value[rejectedField];
        }
        break;
    }
  };

  const sendOptimisticUpdate = (fieldName: string, value: any) => {
    const updateId = generateUpdateId();
    
    optimisticUpdates.value[fieldName] = {
      value,
      status: 'pending',
      updateId,
      timestamp: Date.now()
    };

    socket.value?.send(JSON.stringify({
      type: 'optimistic_update_start',
      payload: {
        updateId,
        tripId,
        fieldName,
        optimisticValue: value,
        clientTimestamp: new Date().toISOString()
      }
    }));
  };

  onMounted(connect);
  onUnmounted(() => {
    socket.value?.close();
  });

  return {
    isConnected,
    activeCollaborators,
    optimisticUpdates,
    sendOptimisticUpdate
  };
}
```

### Connection Management

#### Reconnection Strategy

```typescript
class WebSocketManager {
  private socket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private messageQueue: any[] = [];

  constructor(private url: string, private token: string) {
    this.connect();
  }

  private connect() {
    this.socket = new WebSocket(this.url);
    
    this.socket.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.authenticate();
      this.flushMessageQueue();
    };

    this.socket.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code);
      this.handleReconnection();
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.socket.onmessage = (event) => {
      this.handleMessage(JSON.parse(event.data));
    };
  }

  private handleReconnection() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
      
      console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
      setTimeout(() => this.connect(), delay);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }

  private authenticate() {
    this.sendMessage({
      token: this.token,
      channels: ['global', 'user_specific']
    });
  }

  private flushMessageQueue() {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      this.sendMessage(message);
    }
  }

  public sendMessage(message: any) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    } else {
      // Queue message for when connection is restored
      this.messageQueue.push(message);
    }
  }

  private handleMessage(message: any) {
    // Emit to event listeners
    this.emit('message', message);
  }

  // Event emitter methods
  private listeners: Record<string, Function[]> = {};
  
  public on(event: string, callback: Function) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  private emit(event: string, data: any) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback(data));
    }
  }
}
```

#### Performance Monitoring - WebSocket

```typescript
class WebSocketPerformanceMonitor {
  private metrics = {
    messagesSent: 0,
    messagesReceived: 0,
    bytesSent: 0,
    bytesReceived: 0,
    connectionTime: 0,
    reconnections: 0,
    errors: 0
  };

  private latencyHistory: number[] = [];
  private startTime = Date.now();

  constructor(private wsManager: WebSocketManager) {
    this.setupMonitoring();
  }

  private setupMonitoring() {
    this.wsManager.on('message', (message: any) => {
      this.metrics.messagesReceived++;
      this.metrics.bytesReceived += JSON.stringify(message).length;
      
      // Calculate latency for heartbeat messages
      if (message.type === 'connection_heartbeat' && message.payload.serverTime) {
        const latency = Date.now() - new Date(message.payload.serverTime).getTime();
        this.latencyHistory.push(latency);
        
        // Keep only last 100 measurements
        if (this.latencyHistory.length > 100) {
          this.latencyHistory.shift();
        }
      }
    });

    this.wsManager.on('send', (message: any) => {
      this.metrics.messagesSent++;
      this.metrics.bytesSent += JSON.stringify(message).length;
    });

    this.wsManager.on('reconnect', () => {
      this.metrics.reconnections++;
    });

    this.wsManager.on('error', () => {
      this.metrics.errors++;
    });
  }

  public getMetrics() {
    const uptime = Date.now() - this.startTime;
    const avgLatency = this.latencyHistory.length > 0 
      ? this.latencyHistory.reduce((a, b) => a + b, 0) / this.latencyHistory.length 
      : 0;

    return {
      ...this.metrics,
      uptime,
      averageLatency: avgLatency,
      messagesPerSecond: this.metrics.messagesSent / (uptime / 1000),
      averageMessageSize: this.metrics.bytesSent / this.metrics.messagesSent || 0,
      connectionStability: 1 - (this.metrics.reconnections / (uptime / 60000)), // reconnections per minute
      errorRate: this.metrics.errors / this.metrics.messagesSent || 0
    };
  }

  public reset() {
    this.metrics = {
      messagesSent: 0,
      messagesReceived: 0,
      bytesSent: 0,
      bytesReceived: 0,
      connectionTime: 0,
      reconnections: 0,
      errors: 0
    };
    this.latencyHistory = [];
    this.startTime = Date.now();
  }
}
```

### Testing WebSocket Integration

#### Unit Testing with Jest

```typescript
import { renderHook, act } from '@testing-library/react-hooks';
import { useWebSocket } from '@/hooks/use-websocket';

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  
  constructor(public url: string) {
    MockWebSocket.instances.push(this);
  }

  send = jest.fn();
  close = jest.fn();
  
  // Simulate events
  simulateOpen() {
    this.onopen?.(new Event('open'));
  }

  simulateMessage(data: any) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }

  simulateClose() {
    this.onclose?.(new CloseEvent('close'));
  }
}

describe('useWebSocket', () => {
  beforeEach(() => {
    global.WebSocket = MockWebSocket as any;
    MockWebSocket.instances = [];
  });

  it('should connect and authenticate', async () => {
    const { result } = renderHook(() => useWebSocket({
      url: 'ws://localhost:8000/ws/test',
      token: 'test-token'
    }));

    expect(result.current.connectionState).toBe('connecting');

    // Simulate connection
    act(() => {
      MockWebSocket.instances[0].simulateOpen();
    });

    expect(result.current.connectionState).toBe('connected');
    expect(MockWebSocket.instances[0].send).toHaveBeenCalledWith(
      JSON.stringify({ token: 'test-token' })
    );
  });

  it('should handle optimistic updates', async () => {
    const { result } = renderHook(() => useWebSocket({
      url: 'ws://localhost:8000/ws/test',
      token: 'test-token'
    }));

    // Connect
    act(() => {
      MockWebSocket.instances[0].simulateOpen();
    });

    // Send optimistic update
    act(() => {
      result.current.sendMessage({
        type: 'optimistic_update_start',
        payload: { updateId: 'test-123', fieldName: 'destination', value: 'Paris' }
      });
    });

    // Simulate server confirmation
    act(() => {
      MockWebSocket.instances[0].simulateMessage({
        type: 'optimistic_update_confirmed',
        payload: { updateId: 'test-123', fieldName: 'destination' }
      });
    });

    expect(result.current.lastMessage?.type).toBe('optimistic_update_confirmed');
  });
});
```

#### Integration Testing with Playwright

```typescript
import { test, expect } from '@playwright/test';

test.describe('WebSocket Collaboration', () => {
  test('should handle real-time trip updates', async ({ page, context }) => {
    // Open first user session
    await page.goto('/trips/123');
    await page.waitForSelector('[data-testid="trip-editor"]');

    // Open second user session in new page
    const page2 = await context.newPage();
    await page2.goto('/trips/123');
    await page2.waitForSelector('[data-testid="trip-editor"]');

    // Update trip name in first session
    await page.fill('[data-testid="trip-name-input"]', 'Paris Adventure');
    await page.keyboard.press('Tab'); // Trigger blur event

    // Verify update appears in second session
    await expect(page2.locator('[data-testid="trip-name-input"]')).toHaveValue('Paris Adventure');

    // Verify collaboration indicator shows active user
    await expect(page2.locator('[data-testid="active-collaborators"]')).toContainText('User 1');
  });

  test('should handle connection interruption gracefully', async ({ page }) => {
    await page.goto('/trips/123');
    
    // Simulate network interruption
    await page.setOfflineMode(true);
    
    // Attempt to update trip (should queue update)
    await page.fill('[data-testid="trip-destination"]', 'Rome, Italy');
    
    // Verify optimistic update is shown
    await expect(page.locator('[data-testid="trip-destination"]')).toHaveValue('Rome, Italy');
    await expect(page.locator('[data-testid="pending-changes"]')).toBeVisible();
    
    // Restore network
    await page.setOfflineMode(false);
    
    // Verify update is synchronized
    await expect(page.locator('[data-testid="pending-changes"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="sync-status"]')).toContainText('Synced');
  });
});
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

## Summary

The TripSage WebSocket API provides comprehensive real-time collaboration features including:

- **Real-time Trip Collaboration**: Multi-user editing with presence indicators and conflict resolution
- **Optimistic Updates**: Immediate UI responsiveness with server synchronization and rollback capabilities
- **Advanced Client Integration**: React and Vue.js hooks with TypeScript support
- **Performance Monitoring**: Built-in metrics and connection health monitoring
- **Robust Error Handling**: Comprehensive error codes and automatic reconnection strategies
- **Testing Support**: Unit and integration testing patterns for reliable WebSocket implementations

The API supports both chat-based AI interactions and collaborative trip planning workflows, providing a seamless real-time experience for all TripSage users.

---

*Last updated: 2025-11-06*  
*API Version: 1.0.0*  
*Real-time Collaboration Features: Complete*
