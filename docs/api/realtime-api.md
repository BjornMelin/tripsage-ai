# Realtime API (Supabase)

TripSage uses Supabase Realtime private channels with Row Level Security (no custom socket server).

## Topics & Auth

Topic naming conventions:

| Topic Pattern | Access | Use Case |
|--------------|--------|----------|
| `user:{sub}` | Subject user only | Per-user notifications |
| `session:{uuid}` | Session owner + collaborators | Chat session updates |
| `trip:{trip_id}` | Trip owner + collaborators | Trip collaboration events |

Private channels: clients must authenticate via `supabase.realtime.setAuth(access_token)`; RLS on `realtime.messages` enforces read/write scopes.

## Client Setup (supabase-js v2)

```ts
import { getBrowserClient } from "@/lib/supabase/client";

// Ensure Realtime receives the current access token
export function setRealtimeAuth(accessToken: string | null) {
  const supabase = getBrowserClient();
  if (accessToken) supabase.realtime.setAuth(accessToken);
  else supabase.realtime.setAuth(null);
}

// Join a private channel
export function joinSessionChannel(sessionId: string) {
  const supabase = getBrowserClient();
  const channel = supabase.channel(`session:${sessionId}`, { config: { private: true } });

  channel.on("broadcast", { event: "chat:message" }, (p) => {
    console.log("message", p.payload);
  });

  channel.on("broadcast", { event: "chat:typing" }, (p) => {
    console.log("typing", p.payload);
  });

  channel.subscribe((status) => {
    console.log("realtime status:", status);
  });

  return channel;
}

// Broadcast
export async function sendChatMessage(channel: ReturnType<typeof joinSessionChannel>, payload: any) {
  await channel.send({ type: "broadcast", event: "chat:message", payload });
}
```

### Connection Health (frontend)

- Channel lifecycles managed by `useRealtimeChannel`; status tracked in `useRealtimeConnectionStore` (`connecting/connected/disconnected/reconnecting/error`).
- Store exposes `summary()` for UI badges (see `ConnectionStatusIndicator`), last error timestamp, and `reconnectAll()` with exponential backoff defaults (`src/lib/realtime/backoff.ts`).
- UI components should consume the store instead of mocking statuses:

```tsx
import { ConnectionStatusIndicator } from "@/components/features/realtime/connection-status-monitor";

export function HeaderRealtimeBadge() {
  return <ConnectionStatusIndicator />;
}
```

### Backoff Configuration

Default backoff config in `src/lib/realtime/backoff.ts`:

```ts
const DEFAULT_BACKOFF_CONFIG: BackoffConfig = {
  factor: 2,
  initialDelayMs: 500,
  maxDelayMs: 8000,
};
```

Override per-channel via `useRealtimeChannel(topic, { backoff: customConfig })`.

### Typing Indicators

```ts
// Send typing indicator
channel.send({ type: "broadcast", event: "chat:typing", payload: { userId, isTyping: true } });

// Listen for typing
channel.on("broadcast", { event: "chat:typing" }, (p) => {
  console.log("typing", p.payload);
});
```

## Security

- Auth via `supabase.realtime.setAuth(access_token)`; tokens rotate with session changes.
- RLS policies deny by default and allow only:
  - `user:{sub}`: the subject user.
  - `session:{uuid}`: session owner/collaborators.
- Example policy (realtime.messages):

```sql
CREATE POLICY "private_channels" ON realtime.messages
  FOR ALL USING (
    realtime.topic() LIKE 'user:%' AND auth.uid()::text = split_part(realtime.topic(), ':', 2)
  );
```

## Server-Originated Events

Use database functions or the Realtime REST API with the service role key:

```sql
-- Via database function (requires realtime extension)
SELECT realtime.send('user:123', 'notification', '{"type": "alert", "message": "Trip updated"}');
```

```bash
# Via REST API with service role
curl -X POST 'https://<project>.supabase.co/realtime/v1/broadcast' \
  -H 'Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"topic": "user:123", "event": "notification", "payload": {"type": "alert"}}'
```

Always unsubscribe channels on unmount; `useRealtimeConnectionStore` exposes `reconnectAll()` for exponential backoff when socket drops.

## Connection Management

- **Automatic reconnection**: Supabase handles connection drops; store tracks `reconnecting` status
- **Presence tracking**: Use Supabase presence for online/offline status (not currently implemented)
- **Rate limiting**: Supabase limits channel subscriptions per connection; avoid subscribing to many channels simultaneously
- **Graceful degradation**: UI should show connection status and queue messages during disconnection

## RLS Policy Example

```sql
-- Private channel policy for realtime.messages
CREATE POLICY "private_user_channels" ON realtime.messages
  FOR ALL USING (
    realtime.topic() LIKE 'user:%' AND auth.uid()::text = split_part(realtime.topic(), ':', 2)
  );

CREATE POLICY "private_session_channels" ON realtime.messages
  FOR ALL USING (
    realtime.topic() LIKE 'session:%' AND public.rt_is_session_member()
  );
```

## References

- [Supabase Realtime Authorization](https://supabase.com/docs/guides/realtime/authorization)
- TripSage migrations: `20251122000000_base_schema.sql` (contains `rt_topic_prefix`, `rt_topic_suffix`, `rt_is_session_member`)
