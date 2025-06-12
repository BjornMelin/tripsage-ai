"use client";

import { useAuth } from "@/contexts/auth-context";
import { useSupabase } from "@/lib/supabase/client";
import type { Database, Tables } from "@/lib/supabase/types";
import type {
  RealtimeChannel,
  RealtimePostgresChangesPayload,
} from "@supabase/supabase-js";
import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

type TableName = keyof Database["public"]["Tables"];
type PostgresChangesEvent = "INSERT" | "UPDATE" | "DELETE" | "*";

interface UseRealtimeOptions<T extends TableName> {
  table: T;
  event?: PostgresChangesEvent;
  filter?: string;
  schema?: string;
  onInsert?: (payload: RealtimePostgresChangesPayload<Tables<T>>) => void;
  onUpdate?: (payload: RealtimePostgresChangesPayload<Tables<T>>) => void;
  onDelete?: (payload: RealtimePostgresChangesPayload<Tables<T>>) => void;
  enabled?: boolean;
}

/**
 * Hook for subscribing to real-time database changes
 * Automatically invalidates relevant queries when data changes
 */
export function useSupabaseRealtime<T extends TableName>(
  options: UseRealtimeOptions<T>
) {
  const supabase = useSupabase();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const channelRef = useRef<RealtimeChannel | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [reconnectFlag, setReconnectFlag] = useState(0);

  const {
    table,
    event = "*",
    filter,
    schema = "public",
    onInsert,
    onUpdate,
    onDelete,
    enabled = true,
  } = options;

  const invalidateQueries = useCallback(
    (tableName: string, payload?: any) => {
      // Invalidate all queries related to this table
      queryClient.invalidateQueries({ queryKey: [tableName] });

      // Table-specific invalidations
      switch (tableName) {
        case "trips":
          queryClient.invalidateQueries({ queryKey: ["trips"] });
          queryClient.invalidateQueries({ queryKey: ["trips-infinite"] });
          if (payload?.new?.id) {
            queryClient.invalidateQueries({ queryKey: ["trip", payload.new.id] });
          }
          if (payload?.old?.id) {
            queryClient.invalidateQueries({ queryKey: ["trip", payload.old.id] });
          }
          break;
        case "chat_messages":
          queryClient.invalidateQueries({ queryKey: ["chat-messages"] });
          if (payload?.new?.session_id) {
            queryClient.invalidateQueries({
              queryKey: ["chat-messages", payload.new.session_id],
            });
          }
          break;
        case "trip_collaborators":
          if (payload?.new?.trip_id) {
            queryClient.invalidateQueries({ queryKey: ["trip", payload.new.trip_id] });
          }
          if (payload?.old?.trip_id) {
            queryClient.invalidateQueries({ queryKey: ["trip", payload.old.trip_id] });
          }
          break;
        case "file_attachments":
          queryClient.invalidateQueries({ queryKey: ["files"] });
          if (payload?.new?.trip_id) {
            queryClient.invalidateQueries({
              queryKey: ["trip-files", payload.new.trip_id],
            });
          }
          break;
      }
    },
    [queryClient]
  );

  const handlePayload = useCallback(
    (payload: RealtimePostgresChangesPayload<Tables<T>>) => {
      try {
        setError(null);

        // Call specific event handlers
        switch (payload.eventType) {
          case "INSERT":
            onInsert?.(payload);
            break;
          case "UPDATE":
            onUpdate?.(payload);
            break;
          case "DELETE":
            onDelete?.(payload);
            break;
        }

        // Always invalidate queries for data consistency
        invalidateQueries(table, payload);
      } catch (err) {
        setError(err instanceof Error ? err : new Error("Unknown error occurred"));
      }
    },
    [table, onInsert, onUpdate, onDelete, invalidateQueries]
  );

  useEffect(() => {
    if (!enabled || !user?.id) {
      return;
    }

    try {
      // Create channel with unique name
      const channelName = `realtime-${table}-${user.id}-${Date.now()}`;
      const channel = supabase.channel(channelName);

      // Configure postgres changes listener
      const config: any = {
        event,
        schema,
        table,
      };

      if (filter) {
        config.filter = filter;
      }

      channel.on("postgres_changes", config, handlePayload);

      // Handle connection status
      channel.on("system", {}, (payload) => {
        if (payload.status === "SUBSCRIBED") {
          setIsConnected(true);
          setError(null);
        } else if (payload.status === "CHANNEL_ERROR") {
          setIsConnected(false);
          setError(new Error("Channel subscription error"));
        }
      });

      // Subscribe to the channel
      channel.subscribe((status) => {
        if (status === "SUBSCRIBED") {
          setIsConnected(true);
        } else if (status === "CHANNEL_ERROR") {
          setIsConnected(false);
          setError(new Error("Failed to subscribe to channel"));
        }
      });

      channelRef.current = channel;

      return () => {
        if (channelRef.current) {
          supabase.removeChannel(channelRef.current);
          channelRef.current = null;
          setIsConnected(false);
        }
      };
    } catch (err) {
      setError(
        err instanceof Error ? err : new Error("Failed to setup realtime subscription")
      );
    }
  }, [supabase, table, event, filter, schema, enabled, user?.id, handlePayload, reconnectFlag]);

  const disconnect = useCallback(() => {
    if (channelRef.current) {
      supabase.removeChannel(channelRef.current);
      channelRef.current = null;
      setIsConnected(false);
    }
  }, [supabase]);

  const reconnect = useCallback(() => {
    disconnect();
    // Force a re-render by updating a dependency to trigger useEffect
    setReconnectFlag(prev => prev + 1);
  }, [disconnect]);

  return {
    isConnected,
    error,
    disconnect,
    reconnect,
  };
}

/**
 * Hook for real-time trip collaboration updates
 */
export function useTripRealtime(tripId: number | null) {
  const { user } = useAuth();

  // Subscribe to trip updates
  const tripSubscription = useSupabaseRealtime({
    table: "trips",
    filter: `id=eq.${tripId}`,
    enabled: !!tripId && !!user?.id,
    onUpdate: (payload) => {
      console.log("Trip updated:", payload.new);
      // Could trigger notifications here
    },
  });

  // Subscribe to trip collaborator changes
  const collaboratorSubscription = useSupabaseRealtime({
    table: "trip_collaborators",
    filter: `trip_id=eq.${tripId}`,
    enabled: !!tripId && !!user?.id,
    onInsert: (payload) => {
      console.log("New collaborator added:", payload.new);
      // Could show notification: "User X was added to the trip"
    },
    onDelete: (payload) => {
      console.log("Collaborator removed:", payload.old);
      // Could show notification: "User X was removed from the trip"
    },
  });

  // Subscribe to itinerary item changes
  const itinerarySubscription = useSupabaseRealtime({
    table: "itinerary_items",
    filter: `trip_id=eq.${tripId}`,
    enabled: !!tripId && !!user?.id,
    onInsert: (payload) => {
      console.log("New itinerary item added:", payload.new);
    },
    onUpdate: (payload) => {
      console.log("Itinerary item updated:", payload.new);
    },
    onDelete: (payload) => {
      console.log("Itinerary item deleted:", payload.old);
    },
  });

  const isConnected =
    tripSubscription.isConnected &&
    collaboratorSubscription.isConnected &&
    itinerarySubscription.isConnected;

  const errors = [
    tripSubscription.error,
    collaboratorSubscription.error,
    itinerarySubscription.error,
  ].filter(Boolean);

  return {
    isConnected,
    errors,
    tripSubscription,
    collaboratorSubscription,
    itinerarySubscription,
  };
}

/**
 * Hook for real-time chat message updates
 */
export function useChatRealtime(sessionId: string | null) {
  const { user } = useAuth();
  const [newMessageCount, setNewMessageCount] = useState(0);

  const messagesSubscription = useSupabaseRealtime({
    table: "chat_messages",
    filter: `session_id=eq.${sessionId}`,
    enabled: !!sessionId && !!user?.id,
    onInsert: (payload) => {
      // Don't count user's own messages
      if (payload.new.role !== "user") {
        setNewMessageCount((prev) => prev + 1);
      }
      console.log("New chat message:", payload.new);
    },
  });

  const toolCallsSubscription = useSupabaseRealtime({
    table: "chat_tool_calls",
    enabled: !!sessionId && !!user?.id,
    onUpdate: (payload) => {
      console.log("Tool call updated:", payload.new);
    },
  });

  const clearNewMessageCount = useCallback(() => {
    setNewMessageCount(0);
  }, []);

  return {
    isConnected: messagesSubscription.isConnected && toolCallsSubscription.isConnected,
    errors: [messagesSubscription.error, toolCallsSubscription.error].filter(Boolean),
    newMessageCount,
    clearNewMessageCount,
    messagesSubscription,
    toolCallsSubscription,
  };
}

/**
 * Hook for monitoring real-time connection status across the app
 */
export function useRealtimeStatus() {
  const [globalStatus, setGlobalStatus] = useState<{
    isConnected: boolean;
    connectionCount: number;
    lastError: Error | null;
  }>({
    isConnected: false,
    connectionCount: 0,
    lastError: null,
  });

  // This would be used with a global store to track all active subscriptions
  // For now, it's a placeholder for future implementation

  return globalStatus;
}
