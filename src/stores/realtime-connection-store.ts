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
  lastErrorAt: Date | null;
  channel: RealtimeChannel | null;
}

export interface RealtimeConnectionSummary {
  /** Number of connections currently in "connected" status. */
  connectedCount: number;
  /** Total number of tracked realtime connections. */
  totalCount: number;
  isConnected: boolean;
  /** Most recent error across connections (if any). */
  lastError: Error | null;
  /** Timestamp of the most recent error (if any). */
  lastErrorAt: Date | null;
  reconnectAttempts: number;
  lastReconnectAt: Date | null;
}

interface RealtimeConnectionStore {
  connections: Record<string, RealtimeConnectionEntry>;
  reconnectAttempts: number;
  lastReconnectAt: Date | null;
  isReconnecting: boolean;
  registerChannel: (channel: RealtimeChannel) => void;
  updateStatus: (
    channelId: string,
    state: "idle" | "connecting" | "subscribed" | "error" | "closed",
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
    isReconnecting: false,
    lastReconnectAt: null,

    reconnectAll: async () => {
      if (get().isReconnecting) return;
      set({ isReconnecting: true });
      try {
        const attempts = get().reconnectAttempts + 1;
        const delay = computeBackoffDelay(attempts, DEFAULT_BACKOFF_CONFIG);
        if (delay > 0) {
          await new Promise((resolve) => setTimeout(resolve, delay));
        }

        let hadFailure = false;

        const channels = Object.values(get().connections)
          .map((entry) => entry.channel)
          .filter(Boolean) as RealtimeChannel[];
        for (const channel of channels) {
          try {
            await channel.unsubscribe();
          } catch {
            // ignore
          }
          try {
            if (typeof channel.subscribe === "function") {
              await channel.subscribe();
            }
          } catch (subscribeError) {
            recordClientErrorOnActiveSpan(subscribeError as Error);
            hadFailure = true;
          }
        }

        set({
          lastReconnectAt: new Date(),
          reconnectAttempts: attempts,
        });

        if (hadFailure) {
          throw new Error("Some realtime channels failed to reconnect");
        }
      } finally {
        set({
          isReconnecting: false,
        });
      }
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
            lastErrorAt: null,
            status: "connecting",
          },
        },
      }));
    },

    removeChannel: (channelId) => {
      set((prev) => {
        const next = { ...prev.connections };
        delete next[channelId];
        return { connections: next };
      });
    },

    summary: (() => {
      let cached: RealtimeConnectionSummary | null = null;
      let cachedDeps: {
        activeCount: number;
        totalCount: number;
        lastError: Error | null;
        lastErrorAtMs: number | null;
        lastReconnectAtMs: number | null;
        reconnectAttempts: number;
      } | null = null;

      return () => {
        const connections = Object.values(get().connections);
        const activeCount = connections.filter((c) => c.status === "connected").length;
        const totalCount = connections.length;

        let lastError: Error | null = null;
        let lastErrorAtMs: number | null = null;
        for (const connection of connections) {
          if (connection.lastError && connection.lastErrorAt) {
            const ts = connection.lastErrorAt.getTime();
            if (lastErrorAtMs === null || ts > lastErrorAtMs) {
              lastErrorAtMs = ts;
              lastError = connection.lastError;
            }
          }
        }

        const lastReconnectAtMs = get().lastReconnectAt?.getTime() ?? null;
        const reconnectAttempts = get().reconnectAttempts;

        const nextDeps = {
          activeCount,
          lastError,
          lastErrorAtMs,
          lastReconnectAtMs,
          reconnectAttempts,
          totalCount,
        };

        if (
          cached &&
          cachedDeps &&
          cachedDeps.activeCount === nextDeps.activeCount &&
          cachedDeps.lastError === nextDeps.lastError &&
          cachedDeps.lastErrorAtMs === nextDeps.lastErrorAtMs &&
          cachedDeps.lastReconnectAtMs === nextDeps.lastReconnectAtMs &&
          cachedDeps.reconnectAttempts === nextDeps.reconnectAttempts &&
          cachedDeps.totalCount === nextDeps.totalCount
        ) {
          return cached;
        }

        cachedDeps = nextDeps;
        cached = {
          connectedCount: activeCount,
          isConnected: activeCount > 0,
          lastError,
          lastErrorAt: lastErrorAtMs ? new Date(lastErrorAtMs) : null,
          lastReconnectAt: get().lastReconnectAt,
          reconnectAttempts,
          totalCount,
        };

        return cached;
      };
    })(),

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
        const status = mapChannelStateToStatus(state, hasError);
        const nextError =
          status === "error" || hasError ? (error ?? existing.lastError ?? null) : null;
        const nextErrorAt = nextError ? new Date() : null;
        if (nextError && nextError !== existing.lastError) {
          recordClientErrorOnActiveSpan(nextError);
        }
        return {
          connections: {
            ...prev.connections,
            [channelId]: {
              ...existing,
              lastError: nextError,
              lastErrorAt: nextError ? nextErrorAt : null,
              status,
            },
          },
        };
      });
    },
  })
);
