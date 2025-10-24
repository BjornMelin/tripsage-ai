# WebSocket Integration Guide

This guide covers client integration patterns, testing strategies, error handling, rate limiting, and performance monitoring for TripSage's WebSocket infrastructure.

## Table of Contents

1. [Client Integration](#client-integration)
2. [Testing Strategies](#testing-strategies)
3. [Error Handling](#error-handling)
4. [Rate Limiting](#rate-limiting)
5. [Performance Monitoring](#performance-monitoring)

## Client Integration

### React Hook for WebSocket Management

```typescript
interface UseWebSocketOptions {
  url: string;
  token: string;
  reconnectAttempts?: number;
  heartbeatInterval?: number;
  onMessage?: (message: any) => void;
  onError?: (error: Error) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

interface UseWebSocketReturn {
  connectionState: ConnectionState;
  sendMessage: (message: any) => void;
  lastMessage: any;
  error: Error | null;
  reconnect: () => void;
  disconnect: () => void;
}

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const [connectionState, setConnectionState] =
    useState<ConnectionState>("disconnected");
  const [lastMessage, setLastMessage] = useState<any>(null);
  const [error, setError] = useState<Error | null>(null);

  const connectionRef = useRef<WebSocketConnection | null>(null);
  const lifecycleRef = useRef<ConnectionLifecycleManager | null>(null);

  const sendMessage = useCallback((message: any) => {
    if (connectionRef.current) {
      connectionRef.current.send(message);
    }
  }, []);

  const reconnect = useCallback(() => {
    if (connectionRef.current) {
      connectionRef.current.connect();
    }
  }, []);

  const disconnect = useCallback(() => {
    if (connectionRef.current) {
      connectionRef.current.disconnect();
    }
  }, []);

  useEffect(() => {
    const connection = new WebSocketConnection({
      url: options.url,
      token: options.token,
      reconnectAttempts: options.reconnectAttempts || 3,
      heartbeatInterval: options.heartbeatInterval || 30000,
    });

    const lifecycle = new ConnectionLifecycleManager(connection);

    connectionRef.current = connection;
    lifecycleRef.current = lifecycle;

    // Set up event handlers
    lifecycle.on("stateChange", (state: ConnectionState) => {
      setConnectionState(state);
    });

    connection.on("message", (message: any) => {
      setLastMessage(message);
      options.onMessage?.(message);
    });

    connection.on("error", (error: Error) => {
      setError(error);
      options.onError?.(error);
    });

    // Connect initially
    connection.connect();

    // Cleanup on unmount
    return () => {
      connection.disconnect();
    };
  }, [
    options.url,
    options.token,
    options.reconnectAttempts,
    options.heartbeatInterval,
  ]);

  return {
    connectionState,
    sendMessage,
    lastMessage,
    error,
    reconnect,
    disconnect,
  };
}
```

### Vue.js Composition API

```typescript
import { ref, reactive, onMounted, onUnmounted, watch } from "vue";

export function useWebSocketConnection(options: UseWebSocketOptions) {
  const connectionState = ref<ConnectionState>("disconnected");
  const lastMessage = ref<any>(null);
  const error = ref<Error | null>(null);

  let connection: WebSocketConnection | null = null;
  let lifecycle: ConnectionLifecycleManager | null = null;

  const sendMessage = (message: any) => {
    connection?.send(message);
  };

  const reconnect = () => {
    connection?.connect();
  };

  const disconnect = () => {
    connection?.disconnect();
  };

  const setupConnection = () => {
    connection = new WebSocketConnection({
      url: options.url,
      token: options.token,
      reconnectAttempts: options.reconnectAttempts || 3,
      heartbeatInterval: options.heartbeatInterval || 30000,
    });

    lifecycle = new ConnectionLifecycleManager(connection);

    lifecycle.on("stateChange", (state: ConnectionState) => {
      connectionState.value = state;
    });

    connection.on("message", (message: any) => {
      lastMessage.value = message;
      options.onMessage?.(message);
    });

    connection.on("error", (error: Error) => {
      error.value = error;
      options.onError?.(error);
    });
  };

  const cleanup = () => {
    connection?.disconnect();
    connection = null;
    lifecycle = null;
  };

  onMounted(() => {
    setupConnection();
    connection?.connect();
  });

  onUnmounted(() => {
    cleanup();
  });

  // Watch for option changes
  watch(
    () => [options.url, options.token],
    () => {
      cleanup();
      setupConnection();
      connection?.connect();
    }
  );

  return {
    connectionState: readonly(connectionState),
    lastMessage: readonly(lastMessage),
    error: readonly(error),
    sendMessage,
    reconnect,
    disconnect,
  };
}
```

## Testing Strategies

### Unit Testing Collaboration Features

```typescript
describe("WebSocketConnection", () => {
  let connection: WebSocketConnection;
  let mockWebSocket: any;

  beforeEach(() => {
    mockWebSocket = {
      send: jest.fn(),
      close: jest.fn(),
      readyState: WebSocket.OPEN,
      onopen: null,
      onmessage: null,
      onclose: null,
      onerror: null,
    };

    // Mock WebSocket constructor
    global.WebSocket = jest.fn(() => mockWebSocket);

    connection = new WebSocketConnection({
      url: "ws://test.com",
      token: "test-token",
      reconnectAttempts: 3,
      heartbeatInterval: 30000,
    });
  });

  it("should establish connection successfully", async () => {
    const connectPromise = connection.connect();

    // Simulate successful connection
    mockWebSocket.onopen();

    await connectPromise;
    expect(mockWebSocket.send).toHaveBeenCalledWith(
      JSON.stringify({
        token: "test-token",
      })
    );
  });

  it("should handle connection errors", async () => {
    const connectPromise = connection.connect();

    // Simulate connection error
    mockWebSocket.onerror(new Error("Connection failed"));

    await expect(connectPromise).rejects.toThrow("Connection failed");
  });

  it("should send messages when connected", () => {
    connection.send({ type: "test", data: "hello" });
    expect(mockWebSocket.send).toHaveBeenCalledWith(
      JSON.stringify({
        type: "test",
        data: "hello",
      })
    );
  });

  it("should handle reconnection on close", () => {
    // Simulate unexpected close
    mockWebSocket.onclose({ code: 1006 });

    // Should attempt reconnection
    expect(global.WebSocket).toHaveBeenCalledTimes(2);
  });
});

describe("OptimisticUpdateManager", () => {
  let manager: OptimisticUpdateManager;
  let mockConflictResolver: ConflictResolver;

  beforeEach(() => {
    mockConflictResolver = {
      hasConflict: jest.fn(),
      resolve: jest.fn(),
    };
    manager = new OptimisticUpdateManager(mockConflictResolver);
  });

  it("should apply optimistic updates immediately", async () => {
    const update: OptimisticUpdate = {
      id: "test-update",
      operation: "update",
      resourceType: "trip",
      resourceId: "trip-123",
      data: { name: "New Name" },
      timestamp: Date.now(),
      serverConfirmed: false,
    };

    const uiUpdateSpy = jest.spyOn(manager as any, "applyToUI");

    await manager.applyOptimisticUpdate(update);

    expect(uiUpdateSpy).toHaveBeenCalledWith(update);
    expect(manager["pendingUpdates"].has("test-update")).toBe(true);
  });

  it("should handle server confirmation", async () => {
    // Setup optimistic update
    const update: OptimisticUpdate = {
      id: "test-update",
      operation: "update",
      resourceType: "trip",
      resourceId: "trip-123",
      data: { name: "New Name" },
      timestamp: Date.now(),
      serverConfirmed: false,
    };

    await manager.applyOptimisticUpdate(update);

    // Simulate server confirmation
    await manager.handleServerUpdate({
      resourceId: "trip-123",
      data: { name: "New Name" },
    });

    expect(manager["pendingUpdates"].has("test-update")).toBe(false);
  });
});
```

### Integration Testing with Playwright

```typescript
import { test, expect } from "@playwright/test";

test.describe("Real-time Collaboration", () => {
  test("multiple users can edit trip simultaneously", async ({ context }) => {
    // Create two browser contexts (simulating two users)
    const user1Page = await context.newPage();
    const user2Page = await context.newPage();

    // Navigate both users to the trip editing page
    await user1Page.goto("/trips/trip-123/edit");
    await user2Page.goto("/trips/trip-123/edit");

    // Both users should be connected via WebSocket
    await expect(user1Page.locator(".collaborator-count")).toHaveText("2");
    await expect(user2Page.locator(".collaborator-count")).toHaveText("2");

    // User 1 starts editing the trip name
    await user1Page.locator('input[name="tripName"]').click();
    await user1Page
      .locator('input[name="tripName"]')
      .fill("European Adventure");

    // User 2 should see the editing indicator
    await expect(user2Page.locator(".editing-indicator")).toBeVisible();

    // User 1 saves the change
    await user1Page.locator('button[type="submit"]').click();

    // Both users should see the updated name
    await expect(user1Page.locator('input[name="tripName"]')).toHaveValue(
      "European Adventure"
    );
    await expect(user2Page.locator('input[name="tripName"]')).toHaveValue(
      "European Adventure"
    );

    // User 2 edits the budget
    await user2Page.locator('input[name="budget"]').fill("3500");

    // User 1 should see the change
    await expect(user1Page.locator('input[name="budget"]')).toHaveValue("3500");
  });

  test("should handle connection drops gracefully", async ({ page }) => {
    await page.goto("/trips/trip-123/edit");

    // Simulate WebSocket disconnection
    await page.evaluate(() => {
      // Force disconnect the WebSocket
      window.dispatchEvent(new Event("offline"));
    });

    // Should show disconnected state
    await expect(page.locator(".connection-status")).toHaveText(
      "Reconnecting..."
    );

    // Simulate reconnection
    await page.evaluate(() => {
      window.dispatchEvent(new Event("online"));
    });

    // Should reconnect and show connected state
    await expect(page.locator(".connection-status")).toHaveText("Connected");
  });

  test("should resolve edit conflicts", async ({ context }) => {
    const user1Page = await context.newPage();
    const user2Page = await context.newPage();

    await user1Page.goto("/trips/trip-123/edit");
    await user2Page.goto("/trips/trip-123/edit");

    // Both users edit the same field simultaneously
    await user1Page.locator('input[name="budget"]').fill("3000");
    await user2Page.locator('input[name="budget"]').fill("3500");

    // Should detect conflict and show resolution dialog
    await expect(user1Page.locator(".conflict-dialog")).toBeVisible();
    await expect(user2Page.locator(".conflict-dialog")).toBeVisible();

    // User 1 resolves by choosing their version
    await user1Page.locator(".conflict-dialog .use-mine").click();

    // Both should see user 1's value
    await expect(user1Page.locator('input[name="budget"]')).toHaveValue("3000");
    await expect(user2Page.locator('input[name="budget"]')).toHaveValue("3000");
  });
});
```

## Error Handling

### WebSocket Error Types

| Error Type               | Description                  | Recovery Action                        |
| ------------------------ | ---------------------------- | -------------------------------------- |
| `CONNECTION_FAILED`      | Initial connection failed    | Retry with exponential backoff         |
| `AUTHENTICATION_FAILED`  | Invalid token or credentials | Refresh token or re-authenticate       |
| `AUTHORIZATION_FAILED`   | Insufficient permissions     | Check user permissions                 |
| `RATE_LIMIT_EXCEEDED`    | Too many messages sent       | Implement client-side rate limiting    |
| `MESSAGE_TOO_LARGE`      | Message exceeds size limit   | Compress or split large messages       |
| `INVALID_MESSAGE_FORMAT` | Malformed message            | Validate message format before sending |
| `SERVER_ERROR`           | Internal server error        | Retry request, contact support         |
| `NETWORK_ERROR`          | Network connectivity issues  | Wait for reconnection                  |

### Error Response Format

```json
{
  "id": "error-123",
  "type": "error",
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Invalid or expired token",
    "details": {
      "token_type": "jwt",
      "reason": "expired",
      "expires_at": "2025-01-15T10:30:00Z"
    }
  },
  "timestamp": "2025-01-15T10:35:00Z",
  "request_id": "req-456"
}
```

### Error Handling Best Practices

```typescript
class WebSocketErrorHandler {
  private errorCounts: Map<string, number> = new Map();
  private maxRetries = 3;

  handleError(error: any, context: ErrorContext): ErrorRecoveryAction {
    const errorCode = error.code || "UNKNOWN_ERROR";
    const currentCount = this.errorCounts.get(errorCode) || 0;

    switch (errorCode) {
      case "AUTHENTICATION_FAILED":
        return this.handleAuthError(error, context);

      case "RATE_LIMIT_EXCEEDED":
        return this.handleRateLimitError(error, context);

      case "NETWORK_ERROR":
        return this.handleNetworkError(error, context, currentCount);

      case "SERVER_ERROR":
        return this.handleServerError(error, context, currentCount);

      default:
        return this.handleUnknownError(error, context);
    }
  }

  private handleAuthError(
    error: any,
    context: ErrorContext
  ): ErrorRecoveryAction {
    // Clear invalid tokens
    this.clearStoredTokens();

    // Redirect to login or refresh token
    if (context.canRefreshToken) {
      return { action: "refresh_token", retryAfter: 0 };
    } else {
      return { action: "redirect_login", retryAfter: 0 };
    }
  }

  private handleRateLimitError(
    error: any,
    context: ErrorContext
  ): ErrorRecoveryAction {
    const retryAfter = error.details?.retry_after || 60;
    return { action: "retry", retryAfter };
  }

  private handleNetworkError(
    error: any,
    context: ErrorContext,
    retryCount: number
  ): ErrorRecoveryAction {
    if (retryCount < this.maxRetries) {
      this.errorCounts.set("NETWORK_ERROR", retryCount + 1);
      const retryAfter = Math.min(1000 * Math.pow(2, retryCount), 30000);
      return { action: "retry", retryAfter };
    } else {
      return { action: "fail", message: "Network connection failed" };
    }
  }

  private handleServerError(
    error: any,
    context: ErrorContext,
    retryCount: number
  ): ErrorRecoveryAction {
    if (retryCount < this.maxRetries && error.details?.retryable !== false) {
      this.errorCounts.set("SERVER_ERROR", retryCount + 1);
      const retryAfter = 1000 * Math.pow(2, retryCount);
      return { action: "retry", retryAfter };
    } else {
      return { action: "fail", message: "Server error occurred" };
    }
  }

  private handleUnknownError(
    error: any,
    context: ErrorContext
  ): ErrorRecoveryAction {
    console.error("Unknown WebSocket error:", error);
    return { action: "fail", message: "An unexpected error occurred" };
  }

  private clearStoredTokens(): void {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("refresh_token");
  }
}

interface ErrorContext {
  canRefreshToken: boolean;
  currentUser?: User;
  connectionState: ConnectionState;
}

interface ErrorRecoveryAction {
  action: "retry" | "refresh_token" | "redirect_login" | "fail";
  retryAfter?: number;
  message?: string;
}
```

## Rate Limiting

### WebSocket Rate Limits

| Connection Type    | Messages/Minute | Burst Limit | Window |
| ------------------ | --------------- | ----------- | ------ |
| Chat               | 120             | 20          | 60s    |
| Agent Status       | 60              | 10          | 60s    |
| Trip Collaboration | 300             | 50          | 60s    |
| Notifications      | 30              | 5           | 60s    |

### Rate Limit Headers

WebSocket rate limiting information is sent in control messages:

```json
{
  "type": "rate_limit_status",
  "current_usage": 45,
  "limit": 120,
  "remaining": 75,
  "reset_at": "2025-01-15T11:00:00Z",
  "window_seconds": 60
}
```

### Rate Limit Exceeded Response

```json
{
  "id": "rate-limit-error-123",
  "type": "error",
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Message rate limit exceeded",
    "details": {
      "limit": 120,
      "remaining": 0,
      "retry_after": 30,
      "window_seconds": 60
    }
  },
  "timestamp": "2025-01-15T10:35:00Z"
}
```

### Client-Side Rate Limiting

```typescript
class WebSocketRateLimiter {
  private messageCounts: Map<string, number[]> = new Map();
  private limits: Map<string, { limit: number; window: number }> = new Map();

  constructor() {
    // Set default limits
    this.limits.set("chat", { limit: 120, window: 60000 });
    this.limits.set("agent_status", { limit: 60, window: 60000 });
    this.limits.set("trip_collaboration", { limit: 300, window: 60000 });
    this.limits.set("notifications", { limit: 30, window: 60000 });
  }

  canSendMessage(channelType: string): boolean {
    const limit = this.limits.get(channelType);
    if (!limit) return true;

    const now = Date.now();
    const counts = this.messageCounts.get(channelType) || [];

    // Remove old messages outside the window
    const validCounts = counts.filter(
      (timestamp) => now - timestamp < limit.window
    );

    // Check if under limit
    if (validCounts.length < limit.limit) {
      validCounts.push(now);
      this.messageCounts.set(channelType, validCounts);
      return true;
    }

    return false;
  }

  getTimeUntilNextMessage(channelType: string): number {
    const limit = this.limits.get(channelType);
    if (!limit) return 0;

    const counts = this.messageCounts.get(channelType) || [];
    if (counts.length === 0) return 0;

    const now = Date.now();
    const oldestMessage = Math.min(...counts);
    const timeSinceOldest = now - oldestMessage;

    if (timeSinceOldest >= limit.window) return 0;

    return limit.window - timeSinceOldest;
  }

  getRemainingMessages(channelType: string): number {
    const limit = this.limits.get(channelType);
    if (!limit) return Infinity;

    const counts = this.messageCounts.get(channelType) || [];
    const now = Date.now();

    // Count valid messages in current window
    const validCounts = counts.filter(
      (timestamp) => now - timestamp < limit.window
    );

    return Math.max(0, limit.limit - validCounts.length);
  }
}
```

## Performance Monitoring

### Connection Metrics

```typescript
interface ConnectionMetrics {
  connectionId: string;
  userId: string;
  connectionType: string;
  connectedAt: number;
  lastActivity: number;
  messagesSent: number;
  messagesReceived: number;
  bytesSent: number;
  bytesReceived: number;
  errors: number;
  reconnectAttempts: number;
  averageLatency: number;
  peakLatency: number;
  connectionDrops: number;
}

class WebSocketMetricsCollector {
  private metrics: Map<string, ConnectionMetrics> = new Map();
  private globalMetrics: GlobalMetrics;

  constructor() {
    this.globalMetrics = {
      totalConnections: 0,
      activeConnections: 0,
      totalMessagesSent: 0,
      totalMessagesReceived: 0,
      totalErrors: 0,
      averageLatency: 0,
      uptime: Date.now(),
    };
  }

  recordConnectionEstablished(
    connectionId: string,
    userId: string,
    connectionType: string
  ): void {
    const metrics: ConnectionMetrics = {
      connectionId,
      userId,
      connectionType,
      connectedAt: Date.now(),
      lastActivity: Date.now(),
      messagesSent: 0,
      messagesReceived: 0,
      bytesSent: 0,
      bytesReceived: 0,
      errors: 0,
      reconnectAttempts: 0,
      averageLatency: 0,
      peakLatency: 0,
      connectionDrops: 0,
    };

    this.metrics.set(connectionId, metrics);
    this.globalMetrics.totalConnections++;
    this.globalMetrics.activeConnections++;
  }

  recordMessageSent(
    connectionId: string,
    messageSize: number,
    latency?: number
  ): void {
    const metrics = this.metrics.get(connectionId);
    if (metrics) {
      metrics.messagesSent++;
      metrics.bytesSent += messageSize;
      metrics.lastActivity = Date.now();

      if (latency !== undefined) {
        this.updateLatencyMetrics(metrics, latency);
      }
    }

    this.globalMetrics.totalMessagesSent++;
  }

  recordMessageReceived(connectionId: string, messageSize: number): void {
    const metrics = this.metrics.get(connectionId);
    if (metrics) {
      metrics.messagesReceived++;
      metrics.bytesReceived += messageSize;
      metrics.lastActivity = Date.now();
    }

    this.globalMetrics.totalMessagesReceived++;
  }

  recordError(connectionId: string, error: any): void {
    const metrics = this.metrics.get(connectionId);
    if (metrics) {
      metrics.errors++;
    }

    this.globalMetrics.totalErrors++;
  }

  recordConnectionDropped(connectionId: string): void {
    const metrics = this.metrics.get(connectionId);
    if (metrics) {
      metrics.connectionDrops++;
      this.globalMetrics.activeConnections--;
    }
  }

  private updateLatencyMetrics(
    metrics: ConnectionMetrics,
    latency: number
  ): void {
    // Update rolling average
    const totalMessages = metrics.messagesSent;
    metrics.averageLatency =
      (metrics.averageLatency * (totalMessages - 1) + latency) / totalMessages;
    metrics.peakLatency = Math.max(metrics.peakLatency, latency);
  }

  getConnectionMetrics(connectionId: string): ConnectionMetrics | undefined {
    return this.metrics.get(connectionId);
  }

  getGlobalMetrics(): GlobalMetrics {
    return { ...this.globalMetrics };
  }

  getConnectionsByType(): Map<string, number> {
    const typeCounts = new Map<string, number>();

    for (const metrics of this.metrics.values()) {
      const count = typeCounts.get(metrics.connectionType) || 0;
      typeCounts.set(metrics.connectionType, count + 1);
    }

    return typeCounts;
  }

  cleanupInactiveConnections(maxIdleTime: number = 3600000): void {
    const now = Date.now();
    const toRemove: string[] = [];

    for (const [connectionId, metrics] of this.metrics.entries()) {
      if (now - metrics.lastActivity > maxIdleTime) {
        toRemove.push(connectionId);
      }
    }

    for (const connectionId of toRemove) {
      this.metrics.delete(connectionId);
      this.globalMetrics.activeConnections--;
    }
  }
}

interface GlobalMetrics {
  totalConnections: number;
  activeConnections: number;
  totalMessagesSent: number;
  totalMessagesReceived: number;
  totalErrors: number;
  averageLatency: number;
  uptime: number;
}
```

### Performance Dashboards

```typescript
function WebSocketPerformanceDashboard({
  metrics,
}: {
  metrics: GlobalMetrics;
}) {
  const [realtimeMetrics, setRealtimeMetrics] = useState(metrics);

  useEffect(() => {
    const interval = setInterval(() => {
      // Fetch updated metrics from monitoring service
      fetchMetrics().then(setRealtimeMetrics);
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="performance-dashboard">
      <div className="metric-grid">
        <MetricCard
          title="Active Connections"
          value={realtimeMetrics.activeConnections}
          change={calculateChange(realtimeMetrics.activeConnections)}
          icon="users"
        />
        <MetricCard
          title="Messages/Min"
          value={calculateMessageRate(realtimeMetrics)}
          change={calculateRateChange()}
          icon="message"
        />
        <MetricCard
          title="Average Latency"
          value={`${realtimeMetrics.averageLatency}ms`}
          change={calculateLatencyChange()}
          icon="clock"
        />
        <MetricCard
          title="Error Rate"
          value={`${calculateErrorRate(realtimeMetrics)}%`}
          change={calculateErrorChange()}
          icon="alert"
        />
      </div>

      <div className="charts-section">
        <ConnectionChart data={getConnectionHistory()} />
        <LatencyChart data={getLatencyHistory()} />
        <ErrorChart data={getErrorHistory()} />
      </div>
    </div>
  );
}
```
