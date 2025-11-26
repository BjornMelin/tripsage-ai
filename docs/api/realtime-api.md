# Supabase Realtime Guide

This guide describes TripSage’s final real‑time architecture built on Supabase Realtime with private channels and Row Level Security (RLS). No custom socket server is used.

## Concepts

- Topics: `user:{sub}` for per‑user updates; `session:{uuid}` for chat sessions.
- Private channels: Clients must authenticate and may only join authorized topics.
- Authorization: RLS policies on `realtime.messages` enforce who can read/write each topic.

## Client Setup (supabase-js v2)

```ts
import { getBrowserClient } from "@/lib/supabase/client";

// 1) Ensure Realtime gets the current access token
export function setRealtimeAuth(accessToken: string | null) {
  const supabase = getBrowserClient();
  if (accessToken) supabase.realtime.setAuth(accessToken);
  else supabase.realtime.setAuth(null); // clears auth safely
}

// 2) Join a private channel
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

// 3) Broadcast
export async function sendChatMessage(channel: ReturnType<typeof joinSessionChannel>, payload: any) {
  await channel.send({ type: "broadcast", event: "chat:message", payload });
}
```

### Connection health (frontend)

- All channel lifecycles are managed by the `useRealtimeChannel` hook. Each channel registers in `useRealtimeConnectionStore`, which records status (`connecting/connected/disconnected/reconnecting/error`), last activity, and errors.
- The store exposes `summary()` for lightweight status badges (see `ConnectionStatusIndicator`), surfaces the most recent error/last error timestamp for telemetry, and `reconnectAll()` to unsubscribe/resubscribe with exponential backoff (default config in `src/lib/realtime/backoff.ts`).
- UI components must not hardcode mock status; consume the store instead:

```tsx
import { ConnectionStatusIndicator } from "@/components/features/realtime/connection-status-monitor";

export function HeaderRealtimeBadge() {
  return <ConnectionStatusIndicator />;
}
```

## Security

- Clients authenticate via `supabase.realtime.setAuth(access_token)`; tokens rotate with session changes.
- Policies deny by default and allow only:
  - `user:{sub}`: the subject user.
  - `session:{uuid}`: session owner/collaborators (see migration helpers).

## Server‑originated events

- Use database functions (e.g., `realtime.send`) or the Realtime REST API from the backend with the service role key.

## References

- Supabase Realtime authorization (private channels)
- TripSage migrations: `20251027_01_realtime_policies.sql`, `202510271701_realtime_helpers.sql`
