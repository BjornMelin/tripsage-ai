# Knowledge Pack: Frontend Testing Patterns

## Supabase Realtime Mocking Pattern

### Problem
When testing React hooks that use Supabase Realtime subscriptions, the tests fail due to improper mocking of the Supabase client and RealtimeChannel objects. The main issues are:
1. Method chaining not properly supported in mocks
2. Callbacks not being captured correctly
3. Event simulation not working as expected

### Solution
Created a comprehensive mock helper file that properly simulates Supabase Realtime behavior:

```typescript
// src/test-utils/supabase-realtime-mocks.ts
export type MockRealtimeChannel = {
  on: ReturnType<typeof vi.fn>;
  subscribe: ReturnType<typeof vi.fn>;
  unsubscribe: ReturnType<typeof vi.fn>;
  _callbacks: {
    postgres_changes?: Array<{
      event: string;
      schema: string;
      table: string;
      filter?: string;
      callback: (payload: any) => void;
    }>;
    system?: Array<{
      callback: (payload: any) => void;
    }>;
  };
  _subscribeCallback?: (status: REALTIME_CHANNEL_STATES) => void;
  _isSubscribed?: boolean;
};

export function createMockRealtimeChannel(): MockRealtimeChannel {
  const mockChannel: MockRealtimeChannel = {
    on: vi.fn(),
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
    _callbacks: {
      postgres_changes: [],
      system: [],
    },
    _subscribeCallback: undefined,
  };

  // Setup method chaining
  mockChannel.on.mockImplementation((event: string, configOrCallback: any, callbackOrUndefined?: any) => {
    if (event === "postgres_changes") {
      const config = configOrCallback;
      const callback = callbackOrUndefined;
      mockChannel._callbacks.postgres_changes?.push({
        event: config.event || "*",
        schema: config.schema || "public",
        table: config.table,
        filter: config.filter,
        callback,
      });
    } else if (event === "system") {
      const callback = callbackOrUndefined;
      mockChannel._callbacks.system?.push({ callback });
    }
    return mockChannel;
  });

  mockChannel.subscribe.mockImplementation((callback?: (status: REALTIME_CHANNEL_STATES) => void) => {
    if (callback) {
      mockChannel._subscribeCallback = callback;
    }
    mockChannel._isSubscribed = true;
    return mockChannel;
  });

  mockChannel.unsubscribe.mockImplementation(() => {
    mockChannel._isSubscribed = false;
    return mockChannel;
  });

  return mockChannel;
}
```

### Key Patterns

1. **Method Chaining**: All methods return the channel instance to support chaining
2. **Callback Storage**: Callbacks are stored in internal arrays for later invocation
3. **Event Simulation**: Helper functions to trigger events:
   ```typescript
   simulateChannelSubscription(channel, "SUBSCRIBED");
   simulateSystemEvent(channel, "CHANNEL_ERROR");
   simulatePostgresChange(channel, payload);
   ```

4. **Mock Setup in Tests**:
   ```typescript
   let mockChannel: MockRealtimeChannel;
   let mockSupabaseClient: MockSupabaseClient;
   const mockUseSupabase = vi.fn();

   vi.mock("@/lib/supabase/client", () => ({
     useSupabase: mockUseSupabase,
   }));

   beforeEach(() => {
     mockChannel = createMockRealtimeChannel();
     mockSupabaseClient = createMockSupabaseClient(mockChannel);
     mockUseSupabase.mockReturnValue(mockSupabaseClient);
   });
   ```

### Common Test Patterns

1. **Testing Connection Status**:
   ```typescript
   act(() => {
     simulateChannelSubscription(mockChannel, "SUBSCRIBED");
   });
   
   await waitFor(() => {
     expect(result.current.isConnected).toBe(true);
   });
   ```

2. **Testing Database Change Events**:
   ```typescript
   const mockPayload = {
     eventType: "INSERT",
     new: { id: 1, name: "Test" },
     old: {},
     schema: "public",
     table: "trips",
   };
   
   act(() => {
     simulatePostgresChange(mockChannel, mockPayload);
   });
   
   expect(onInsert).toHaveBeenCalledWith(mockPayload);
   ```

3. **Testing Multiple Channels**:
   ```typescript
   const channels = new Map<string, MockRealtimeChannel>();
   mockSupabaseClient.channel.mockImplementation((name: string) => {
     if (!channels.has(name)) {
       channels.set(name, createMockRealtimeChannel());
     }
     return channels.get(name)!;
   });
   ```

### Debugging Tips

1. **Check Hook Return Values**: Always verify the hook returns the expected structure before testing specific properties
2. **Use waitFor**: Many realtime operations are async, use `waitFor` to ensure state updates
3. **Mock Before Import**: Ensure mocks are set up before importing the components/hooks being tested
4. **Clear Mocks**: Always clear mocks in beforeEach to prevent test pollution

### Future Improvements

1. Add filter parsing to properly match Postgres filter strings
2. Create type-safe event payloads for different table types
3. Add support for presence and broadcast event types
4. Create integration test utilities for end-to-end realtime testing