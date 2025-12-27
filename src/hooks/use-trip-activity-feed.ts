/**
 * @fileoverview Ephemeral trip activity feed over Supabase Realtime broadcast.
 */

"use client";

import { useCallback, useMemo, useState } from "react";
import { useRealtimeChannel } from "@/hooks/supabase/use-realtime-channel";
import { nowIso, secureId } from "@/lib/security/random";

export type TripActivityKind =
  | "collaborator_invited"
  | "collaborator_removed"
  | "collaborator_role_updated"
  | "trip_updated";

export type TripActivityBroadcastPayload = {
  kind: TripActivityKind;
  message: string;
  at: string;
};

export type TripActivityItem = TripActivityBroadcastPayload & {
  id: string;
  source: "local" | "remote";
};

const ACTIVITY_EVENT = "trip:activity";
const MAX_EVENTS = 20;

export function useTripActivityFeed(tripId: number | null) {
  const [events, setEvents] = useState<TripActivityItem[]>([]);

  const topic = useMemo(() => {
    if (tripId === null) return null;
    if (!Number.isFinite(tripId)) return null;
    return `trip:${tripId}`;
  }, [tripId]);

  const channel = useRealtimeChannel<TripActivityBroadcastPayload>(topic, {
    events: [ACTIVITY_EVENT],
    onMessage: (payload) => {
      const item: TripActivityItem = {
        ...payload,
        id: secureId(),
        source: "remote",
      };

      setEvents((prev) => [item, ...prev].slice(0, MAX_EVENTS));
    },
    private: true,
  });

  const emit = useCallback(
    async (input: Omit<TripActivityBroadcastPayload, "at"> & { at?: string }) => {
      const payload: TripActivityBroadcastPayload = {
        at: input.at ?? nowIso(),
        kind: input.kind,
        message: input.message,
      };

      // Always update local UI, even when offline.
      const item: TripActivityItem = { ...payload, id: secureId(), source: "local" };
      setEvents((prev) => [item, ...prev].slice(0, MAX_EVENTS));

      try {
        await channel.sendBroadcast(ACTIVITY_EVENT, payload);
      } catch {
        // Ignore broadcast failures; local entry already recorded.
      }
    },
    [channel]
  );

  return {
    connectionStatus: channel.connectionStatus,
    emit,
    error: channel.error,
    events,
  };
}
