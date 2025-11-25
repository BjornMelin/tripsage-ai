/**
 * @fileoverview Global store for Supabase Realtime connection health.
 */

import type { ConnectionStatus } from "@schemas/realtime";
import type { RealtimeChannel } from "@supabase/supabase-js";
import { create } from "zustand";
import { computeBackoffDelay, DEFAULT_BACKOFF_CONFIG } from "@/lib/realtime/backoff";
import { mapChannelStateToStatus } from "@/lib/realtime/status";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";

export interface RealtimeConnectionEntry {
  id: string;
  status: ConnectionStatus;
  lastActivity: Date | null;
  lastError: Error | null;
  channel: RealtimeChannel | null;
}

export interface RealtimeConnectionSummary {
  isConnected: boolean;
  connectionCount: number;
  lastError: Error | null;
  reconnectAttempts: number;
  lastReconnectAt: Date | null;
}

interface RealtimeConnectionStore {
  connections: Record<string, RealtimeConnectionEntry>;
  reconnectAttempts: number;
  lastReconnectAt: Date | null;
  registerChannel: (channel: RealtimeChannel) => void;
  updateStatus: (
    channelId: string,
    state: string,
    hasError: boolean,
    error?: Error | null
  ) => void;
  updateActivity: (channelId: string) => void;
  removeChannel: (channelId: string) => void;
  reconnectAll: () => Promise<void>;
  summary: () => RealtimeConnectionSummary;
}

export const useRealtimeConnectionStore = create<RealtimeConnectionStore>(
  (set, get) => ({
    connections: {},
    lastReconnectAt: null,

    reconnectAll: async () => {
      const attempts = get().reconnectAttempts + 1;
      const delay = computeBackoffDelay(attempts, DEFAULT_BACKOFF_CONFIG);
      if (delay > 0) {
        await new Promise((resolve) => setTimeout(resolve, delay));
      }

      const channels = Object.values(get().connections)
        .map((entry) => entry.channel)
        .filter(Boolean) as RealtimeChannel[];
      for (const channel of channels) {
        try {
          await channel.unsubscribe();
        } catch {
          // ignore
        }
        if (typeof channel.subscribe === "function") {
          channel.subscribe();
        }
      }

      set({
        lastReconnectAt: new Date(),
        reconnectAttempts: attempts,
      });
    },

    reconnectAttempts: 0,

    registerChannel: (channel) => {
      const id = channel.topic;
      set((state) => ({
        connections: {
          ...state.connections,
          [id]: {
            channel,
            id,
            lastActivity: null,
            lastError: null,
            status: "connecting",
          },
        },
      }));
    },

    removeChannel: (channelId) => {
      set((prev) => {
        const next = { ...prev.connections };
        delete next[channelId];
        return { connections: next } as RealtimeConnectionStore;
      });
    },

    summary: () => {
      const connections = Object.values(get().connections);
      const active = connections.filter((c) => c.status === "connected");
      const lastError = connections.find((c) => c.lastError)?.lastError ?? null;

      return {
        connectionCount: active.length,
        isConnected: active.length > 0,
        lastError,
        lastReconnectAt: get().lastReconnectAt,
        reconnectAttempts: get().reconnectAttempts,
      };
    },

    updateActivity: (channelId) => {
      set((prev) => {
        const existing = prev.connections[channelId];
        if (!existing) return prev;
        return {
          connections: {
            ...prev.connections,
            [channelId]: {
              ...existing,
              lastActivity: new Date(),
            },
          },
        };
      });
    },

    updateStatus: (channelId, state, hasError, error) => {
      set((prev) => {
        const existing = prev.connections[channelId];
        if (!existing) return prev;
        const status = mapChannelStateToStatus(
          state as "idle" | "connecting" | "subscribed" | "error" | "closed",
          hasError
        );
        const lastError =
          status === "error" || hasError ? (error ?? existing.lastError ?? null) : null;
        if (lastError) {
          recordClientErrorOnActiveSpan(lastError);
        }
        return {
          connections: {
            ...prev.connections,
            [channelId]: {
              ...existing,
              lastError,
              status,
            },
          },
        };
      });
    },
  })
);
