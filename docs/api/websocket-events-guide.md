# WebSocket Events Guide

This guide covers TripSage's WebSocket event types, real-time collaboration features, and optimistic update patterns for building interactive applications.

## Table of Contents

1. [Event Types](#event-types)
2. [Real-time Collaboration](#real-time-collaboration)
3. [Optimistic Updates](#optimistic-updates)

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
  "session_id": "session-456",
  "role": "user",
  "content": "Help me plan a trip to Paris",
  "timestamp": "2025-01-15T10:30:00Z",
  "metadata": {
    "user_id": "user-789",
    "message_type": "text",
    "attachments": []
  },
  "tool_calls": []
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
  "session_id": "session-456",
  "chunk": "I'd be happy to help",
  "is_complete": false,
  "sequence": 1
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
  "session_id": "session-456",
  "full_content": "I'd be happy to help you plan your Paris trip...",
  "total_chunks": 5
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
  "session_id": "session-456",
  "user_id": "user-789",
  "timestamp": "2025-01-15T10:30:00Z"
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
  "session_id": "session-456",
  "user_id": "user-789",
  "timestamp": "2025-01-15T10:30:05Z"
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
  "session_id": "session-456",
  "tool_name": "flight_search",
  "parameters": {
    "origin": "NYC",
    "destination": "PAR",
    "departure_date": "2025-06-01"
  },
  "timestamp": "2025-01-15T10:30:10Z"
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
  "session_id": "session-456",
  "tool_name": "flight_search",
  "progress": 0.75,
  "message": "Searching for return flights...",
  "timestamp": "2025-01-15T10:30:15Z"
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
  "session_id": "session-456",
  "tool_name": "flight_search",
  "result": {
    "flights_found": 25,
    "cheapest_price": 450,
    "currency": "USD"
  },
  "timestamp": "2025-01-15T10:30:20Z"
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
  "session_id": "session-456",
  "tool_name": "flight_search",
  "error": {
    "code": "EXTERNAL_API_ERROR",
    "message": "Flight search service temporarily unavailable",
    "retryable": true
  },
  "timestamp": "2025-01-15T10:30:25Z"
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
  "session_id": "session-456",
  "agent_id": "agent-789",
  "status": "active",
  "current_task": "Analyzing flight options",
  "progress": 0.6,
  "timestamp": "2025-01-15T10:30:30Z"
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
  "session_id": "session-456",
  "task_id": "task-101",
  "task_name": "Flight Search",
  "description": "Searching for flights from NYC to PAR",
  "estimated_duration": 30,
  "timestamp": "2025-01-15T10:30:35Z"
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
  "session_id": "session-456",
  "task_id": "task-101",
  "progress": 0.8,
  "message": "Found 15 matching flights",
  "timestamp": "2025-01-15T10:30:40Z"
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
  "session_id": "session-456",
  "task_id": "task-101",
  "result": {
    "flights": 15,
    "price_range": "450-1200 USD",
    "best_option": "flight-123"
  },
  "timestamp": "2025-01-15T10:30:45Z"
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
  "user_id": "user-789",
  "session_id": "session-456",
  "server_version": "1.0.0",
  "features": ["chat", "realtime", "collaboration"],
  "timestamp": "2025-01-15T10:30:00Z"
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
  "timestamp": "2025-01-15T10:30:50Z",
  "sequence": 1
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
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Invalid token provided",
    "details": {
      "token_type": "jwt",
      "reason": "expired"
    }
  },
  "timestamp": "2025-01-15T10:30:55Z"
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
  "reason": "server_maintenance",
  "reconnect_after": 300,
  "timestamp": "2025-01-15T10:31:00Z"
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
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred",
    "details": {
      "request_id": "req-456",
      "component": "chat_service"
    }
  },
  "timestamp": "2025-01-15T10:31:05Z"
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
  "level": "info",
  "title": "System Update",
  "message": "Scheduled maintenance in 30 minutes",
  "action_url": "/status",
  "timestamp": "2025-01-15T10:31:10Z"
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
  "priority": "high",
  "message": "All services will be unavailable for maintenance from 2:00-3:00 UTC",
  "timestamp": "2025-01-15T10:31:15Z"
}
```

## Real-time Collaboration

TripSage's WebSocket infrastructure provides real-time collaboration features for trip planning, editing, and multi-user coordination.

### Trip Collaboration Events

#### `trip_collaboration_join`

User joins a trip collaboration session.

**Direction:** Bidirectional

**Payload:**

```json
{
  "id": "collab-join-123",
  "type": "trip_collaboration_join",
  "trip_id": "trip-456",
  "user_id": "user-789",
  "user_name": "John Doe",
  "permissions": ["read", "write"],
  "cursor_position": null,
  "timestamp": "2025-01-15T10:31:20Z"
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
  "trip_id": "trip-456",
  "user_id": "user-789",
  "reason": "user_disconnected",
  "timestamp": "2025-01-15T10:31:25Z"
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
  "trip_id": "trip-456",
  "user_id": "user-789",
  "field_name": "destination",
  "field_value": "Paris, France",
  "timestamp": "2025-01-15T10:31:30Z"
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
  "trip_id": "trip-456",
  "user_id": "user-789",
  "field_name": "destination",
  "final_value": "Paris, France",
  "timestamp": "2025-01-15T10:31:35Z"
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
  "trip_id": "trip-456",
  "updated_by": "user-789",
  "changes": [
    {
      "field": "budget",
      "old_value": 3000,
      "new_value": 3500,
      "timestamp": "2025-01-15T10:31:40Z"
    }
  ],
  "full_trip_data": {
    "id": "trip-456",
    "name": "European Adventure",
    "budget": 3500,
    "destinations": ["Paris", "Rome"]
  },
  "timestamp": "2025-01-15T10:31:40Z"
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
  "trip_id": "trip-456",
  "collaborators": [
    {
      "user_id": "user-789",
      "user_name": "John Doe",
      "status": "active",
      "last_seen": "2025-01-15T10:31:45Z",
      "current_field": "itinerary",
      "cursor_position": {
        "x": 150,
        "y": 200,
        "element_id": "day-1-activity-1"
      }
    },
    {
      "user_id": "user-012",
      "user_name": "Jane Smith",
      "status": "idle",
      "last_seen": "2025-01-15T10:31:30Z",
      "current_field": null,
      "cursor_position": null
    }
  ],
  "timestamp": "2025-01-15T10:31:45Z"
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
  "trip_id": "trip-456",
  "field_name": "budget",
  "conflicting_changes": [
    {
      "user_id": "user-789",
      "value": 3500,
      "timestamp": "2025-01-15T10:31:40Z"
    },
    {
      "user_id": "user-012",
      "value": 3200,
      "timestamp": "2025-01-15T10:31:42Z"
    }
  ],
  "resolution_required": true,
  "timestamp": "2025-01-15T10:31:50Z"
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
  "trip_id": "trip-456",
  "user_id": "user-012",
  "old_permissions": ["read"],
  "new_permissions": ["read", "write"],
  "changed_by": "user-789",
  "timestamp": "2025-01-15T10:31:55Z"
}
```

## Optimistic Updates

### Core Optimistic Update System

```typescript
interface OptimisticUpdate {
  id: string;
  operation: "create" | "update" | "delete";
  resourceType: string;
  resourceId: string;
  data: any;
  timestamp: number;
  serverConfirmed: boolean;
  rollbackData?: any;
}

class OptimisticUpdateManager {
  private pendingUpdates: Map<string, OptimisticUpdate> = new Map();
  private conflictResolver: ConflictResolver;

  constructor(conflictResolver: ConflictResolver) {
    this.conflictResolver = conflictResolver;
  }

  async applyOptimisticUpdate(update: OptimisticUpdate): Promise<void> {
    // Store rollback data
    update.rollbackData = await this.getCurrentState(
      update.resourceType,
      update.resourceId
    );

    // Apply update immediately to UI
    await this.applyToUI(update);

    // Store pending update
    this.pendingUpdates.set(update.id, update);

    // Send to server
    try {
      await this.sendToServer(update);
      update.serverConfirmed = true;
    } catch (error) {
      await this.handleUpdateFailure(update, error);
    }
  }

  private async applyToUI(update: OptimisticUpdate): Promise<void> {
    switch (update.operation) {
      case "create":
        await this.uiCreate(update.resourceType, update.data);
        break;
      case "update":
        await this.uiUpdate(
          update.resourceType,
          update.resourceId,
          update.data
        );
        break;
      case "delete":
        await this.uiDelete(update.resourceType, update.resourceId);
        break;
    }
  }

  private async sendToServer(update: OptimisticUpdate): Promise<void> {
    const response = await fetch(
      `/api/${update.resourceType}/${update.resourceId}`,
      {
        method: this.getHttpMethod(update.operation),
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(update.data),
      }
    );

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }
  }

  private async handleUpdateFailure(
    update: OptimisticUpdate,
    error: any
  ): Promise<void> {
    // Rollback the optimistic update
    if (update.rollbackData) {
      await this.rollbackUpdate(update);
    }

    // Remove from pending updates
    this.pendingUpdates.delete(update.id);

    // Notify user of failure
    this.notifyUser("Update failed", error.message);
  }

  private async rollbackUpdate(update: OptimisticUpdate): Promise<void> {
    if (update.rollbackData) {
      await this.applyToUI({
        ...update,
        data: update.rollbackData,
        operation:
          update.operation === "create"
            ? "delete"
            : update.operation === "delete"
            ? "create"
            : "update",
      });
    }
  }

  async handleServerUpdate(serverUpdate: any): Promise<void> {
    const pendingUpdate = Array.from(this.pendingUpdates.values()).find(
      (update) => update.resourceId === serverUpdate.resourceId
    );

    if (pendingUpdate) {
      if (this.conflictResolver.hasConflict(pendingUpdate, serverUpdate)) {
        await this.conflictResolver.resolve(pendingUpdate, serverUpdate);
      } else {
        // No conflict, confirm the update
        pendingUpdate.serverConfirmed = true;
        this.pendingUpdates.delete(pendingUpdate.id);
      }
    } else {
      // No pending update, apply server update directly
      await this.applyToUI(serverUpdate);
    }
  }

  private getHttpMethod(operation: string): string {
    switch (operation) {
      case "create":
        return "POST";
      case "update":
        return "PUT";
      case "delete":
        return "DELETE";
      default:
        return "GET";
    }
  }

  // Abstract methods to be implemented by subclasses
  protected async getCurrentState(
    resourceType: string,
    resourceId: string
  ): Promise<any> {
    throw new Error("getCurrentState must be implemented");
  }

  protected async uiCreate(resourceType: string, data: any): Promise<void> {
    throw new Error("uiCreate must be implemented");
  }

  protected async uiUpdate(
    resourceType: string,
    resourceId: string,
    data: any
  ): Promise<void> {
    throw new Error("uiUpdate must be implemented");
  }

  protected async uiDelete(
    resourceType: string,
    resourceId: string
  ): Promise<void> {
    throw new Error("uiDelete must be implemented");
  }

  protected notifyUser(title: string, message: string): void {
    // Implementation for user notifications
  }
}
```

### React Integration for Optimistic Updates

```typescript
function useOptimisticTripUpdate(tripId: string) {
  const [optimisticState, setOptimisticState] = useState<any>({});
  const [pendingUpdates, setPendingUpdates] = useState<Set<string>>(new Set());

  const updateTripField = useCallback(
    async (fieldName: string, value: any, optimistic = true) => {
      const updateId = `${fieldName}-${Date.now()}`;

      if (optimistic) {
        // Apply optimistic update immediately
        setOptimisticState((prev) => ({
          ...prev,
          [fieldName]: value,
        }));
        setPendingUpdates((prev) => new Set(prev).add(updateId));
      }

      try {
        const response = await fetch(`/api/trips/${tripId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ [fieldName]: value }),
        });

        if (!response.ok) {
          throw new Error("Update failed");
        }

        // Confirm update
        setPendingUpdates((prev) => {
          const newSet = new Set(prev);
          newSet.delete(updateId);
          return newSet;
        });
      } catch (error) {
        // Rollback optimistic update
        setOptimisticState((prev) => {
          const newState = { ...prev };
          delete newState[fieldName];
          return newState;
        });
        setPendingUpdates((prev) => {
          const newSet = new Set(prev);
          newSet.delete(updateId);
          return newSet;
        });

        throw error;
      }
    },
    [tripId]
  );

  return {
    optimisticState,
    pendingUpdates: Array.from(pendingUpdates),
    updateTripField,
  };
}

// Usage in component
function TripEditor({ tripId }: { tripId: string }) {
  const { optimisticState, pendingUpdates, updateTripField } =
    useOptimisticTripUpdate(tripId);
  const [serverTrip, setServerTrip] = useState<any>(null);

  // Merge server state with optimistic updates
  const displayTrip = useMemo(
    () => ({
      ...serverTrip,
      ...optimisticState,
    }),
    [serverTrip, optimisticState]
  );

  const handleFieldChange = async (fieldName: string, value: any) => {
    try {
      await updateTripField(fieldName, value, true);
    } catch (error) {
      // Handle error (show toast, etc.)
      console.error("Failed to update trip:", error);
    }
  };

  return (
    <div>
      <input
        value={displayTrip?.name || ""}
        onChange={(e) => handleFieldChange("name", e.target.value)}
        disabled={pendingUpdates.some((id) => id.startsWith("name-"))}
      />
      {pendingUpdates.some((id) => id.startsWith("name-")) && (
        <span>Saving...</span>
      )}
    </div>
  );
}
```

### Conflict Resolution Implementation

```typescript
interface Conflict {
  id: string;
  fieldName: string;
  localValue: any;
  serverValue: any;
  localTimestamp: number;
  serverTimestamp: number;
  resolved: boolean;
}

interface ConflictResolution {
  strategy: "server-wins" | "client-wins" | "manual" | "merge";
  resolvedValue?: any;
  resolvedBy?: string;
  resolvedAt?: number;
}

class ConflictResolver {
  private conflicts: Map<string, Conflict> = new Map();

  hasConflict(localUpdate: OptimisticUpdate, serverUpdate: any): boolean {
    // Check if both updates modify the same field
    return (
      localUpdate.data &&
      serverUpdate.data &&
      Object.keys(localUpdate.data).some(
        (key) =>
          serverUpdate.data.hasOwnProperty(key) &&
          localUpdate.data[key] !== serverUpdate.data[key]
      )
    );
  }

  async resolve(
    localUpdate: OptimisticUpdate,
    serverUpdate: any
  ): Promise<ConflictResolution> {
    const conflictId = `${localUpdate.resourceId}-${Date.now()}`;
    const conflict: Conflict = {
      id: conflictId,
      fieldName: Object.keys(localUpdate.data)[0], // Simplified for single field
      localValue: localUpdate.data[Object.keys(localUpdate.data)[0]],
      serverValue: serverUpdate.data[Object.keys(serverUpdate.data)[0]],
      localTimestamp: localUpdate.timestamp,
      serverTimestamp: serverUpdate.timestamp,
      resolved: false,
    };

    this.conflicts.set(conflictId, conflict);

    // Auto-resolve based on strategy
    const resolution = await this.autoResolve(conflict);

    conflict.resolved = true;
    conflict.resolvedBy = "auto";
    conflict.resolvedAt = Date.now();

    return resolution;
  }

  private async autoResolve(conflict: Conflict): Promise<ConflictResolution> {
    // Strategy 1: Server wins (most common for collaborative editing)
    if (conflict.serverTimestamp > conflict.localTimestamp) {
      return {
        strategy: "server-wins",
        resolvedValue: conflict.serverValue,
      };
    }

    // Strategy 2: Client wins (if local change is more recent)
    return {
      strategy: "client-wins",
      resolvedValue: conflict.localValue,
    };
  }

  async manualResolve(
    conflictId: string,
    resolvedValue: any,
    userId: string
  ): Promise<void> {
    const conflict = this.conflicts.get(conflictId);
    if (conflict) {
      conflict.resolved = true;
      conflict.resolvedBy = userId;
      conflict.resolvedAt = Date.now();

      // Update UI with resolved value
      await this.applyResolution(conflict, resolvedValue);
    }
  }

  private async applyResolution(
    conflict: Conflict,
    resolvedValue: any
  ): Promise<void> {
    // Update UI with resolved value
    // This would integrate with the optimistic update manager
  }

  getActiveConflicts(): Conflict[] {
    return Array.from(this.conflicts.values()).filter((c) => !c.resolved);
  }
}
```
