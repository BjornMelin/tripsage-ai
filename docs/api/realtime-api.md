# Realtime API (Supabase)

TripSage uses Supabase Realtime private channels with Row Level Security (no custom socket server).

## Topics & Auth

- Topics: `user:{sub}` for per-user updates; `session:{uuid}` for chat sessions.
- Private channels: clients must authenticate; RLS on `realtime.messages` enforces read/write scopes.

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

## Security

- Auth via `supabase.realtime.setAuth(access_token)`; tokens rotate with session changes.
- RLS policies deny by default and allow only:
  - `user:{sub}`: the subject user.
  - `session:{uuid}`: session owner/collaborators.

## Server-Originated Events

- Use database functions (e.g., `realtime.send`) or the Realtime REST API with the service role key.

## References

- Supabase Realtime authorization (private channels)
- TripSage migrations: `20251027_01_realtime_policies.sql`, `202510271701_realtime_helpers.sql`
