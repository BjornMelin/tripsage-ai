/**
 * Real-time Supabase subscriptions with React Query integration
 * Provides live updates for collaborative features and real-time data sync
 */

import { useEffect, useCallback, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useSupabase } from "@/lib/supabase/client";
import type { Database, Tables } from "@/lib/supabase/database.types";
import type { RealtimeChannel, RealtimePostgresChangesPayload } from "@supabase/supabase-js";

export interface RealtimeSubscriptionOptions<T extends keyof Database["public"]["Tables"]> {
  table: T;
  event?: "INSERT" | "UPDATE" | "DELETE" | "*";
  schema?: string;
  filter?: string;
  onInsert?: (payload: RealtimePostgresChangesPayload<Tables<T>>) => void;
  onUpdate?: (payload: RealtimePostgresChangesPayload<Tables<T>>) => void;
  onDelete?: (payload: RealtimePostgresChangesPayload<Tables<T>>) => void;
  autoInvalidateQueries?: boolean;
}

/**
 * Hook for subscribing to real-time database changes
 * Automatically integrates with React Query for cache updates
 */
export function useSupabaseRealtime<T extends keyof Database["public"]["Tables"]>(
  options: RealtimeSubscriptionOptions<T>
) {
  const supabase = useSupabase();
  const queryClient = useQueryClient();
  const channelRef = useRef<RealtimeChannel | null>(null);
  const {
    table,
    event = "*",
    schema = "public",
    filter,
    onInsert,
    onUpdate,
    onDelete,
    autoInvalidateQueries = true,
  } = options;

  const handleInsert = useCallback(
    (payload: RealtimePostgresChangesPayload<Tables<T>>) => {
      if (autoInvalidateQueries) {
        queryClient.invalidateQueries({ queryKey: [table] });
      }
      onInsert?.(payload);
    },
    [table, queryClient, autoInvalidateQueries, onInsert]
  );

  const handleUpdate = useCallback(
    (payload: RealtimePostgresChangesPayload<Tables<T>>) => {
      if (autoInvalidateQueries && payload.new) {
        // Update specific item in cache
        queryClient.setQueryData([table, "single", payload.new.id], payload.new);
        // Invalidate table queries
        queryClient.invalidateQueries({ queryKey: [table] });
      }
      onUpdate?.(payload);
    },
    [table, queryClient, autoInvalidateQueries, onUpdate]
  );

  const handleDelete = useCallback(
    (payload: RealtimePostgresChangesPayload<Tables<T>>) => {
      if (autoInvalidateQueries && payload.old) {
        // Remove from cache
        queryClient.removeQueries({ queryKey: [table, "single", payload.old.id] });
        // Invalidate table queries
        queryClient.invalidateQueries({ queryKey: [table] });
      }
      onDelete?.(payload);
    },
    [table, queryClient, autoInvalidateQueries, onDelete]
  );

  useEffect(() => {
    const channelName = `realtime:${table}`;
    const channel = supabase.channel(channelName);

    const subscriptionConfig = {
      event,
      schema,
      table,
      ...(filter && { filter }),
    };

    channel.on(
      "postgres_changes",
      subscriptionConfig,
      (payload: RealtimePostgresChangesPayload<Tables<T>>) => {
        switch (payload.eventType) {
          case "INSERT":
            handleInsert(payload);
            break;
          case "UPDATE":
            handleUpdate(payload);
            break;
          case "DELETE":
            handleDelete(payload);
            break;
        }
      }
    );

    channel.subscribe((status) => {
      if (status === "SUBSCRIBED") {
        console.log(`✅ Subscribed to ${table} real-time updates`);
      } else if (status === "CHANNEL_ERROR") {
        console.error(`❌ Failed to subscribe to ${table} real-time updates`);
      }
    });

    channelRef.current = channel;

    return () => {
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current);
        console.log(`🔌 Unsubscribed from ${table} real-time updates`);
      }
    };
  }, [table, event, schema, filter, handleInsert, handleUpdate, handleDelete, supabase]);

  return {
    channel: channelRef.current,
    unsubscribe: () => {
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current);
        channelRef.current = null;
      }
    },
  };
}

/**
 * Hook for trip collaboration real-time updates
 * Optimized for collaborative trip planning features
 */
export function useTripCollaborationRealtime(tripId: number | null) {
  return useSupabaseRealtime({
    table: "trips",
    filter: tripId ? `id=eq.${tripId}` : undefined,
    onUpdate: (payload) => {
      console.log("🚀 Trip updated:", payload.new);
    },
  });
}

/**
 * Hook for chat session real-time updates
 * Handles live chat message updates
 */
export function useChatRealtime(sessionId: string | null) {
  const queryClient = useQueryClient();

  return useSupabaseRealtime({
    table: "chat_messages",
    filter: sessionId ? `session_id=eq.${sessionId}` : undefined,
    onInsert: (payload) => {
      console.log("💬 New chat message:", payload.new);
      // Add to chat messages cache optimistically
      if (payload.new) {
        queryClient.setQueryData(
          ["chat_messages", sessionId],
          (old: Tables<"chat_messages">[] | undefined) => {
            return old ? [...old, payload.new] : [payload.new];
          }
        );
      }
    },
  });
}

/**
 * Hook for file attachment real-time updates
 * Monitors upload progress and completion
 */
export function useFileAttachmentRealtime(userId: string | null) {
  return useSupabaseRealtime({
    table: "file_attachments",
    filter: userId ? `user_id=eq.${userId}` : undefined,
    onUpdate: (payload) => {
      console.log("📎 File attachment updated:", payload.new);
    },
  });
}

/**
 * Hook for trip collaborator real-time updates
 * Monitors who joins/leaves trip collaboration
 */
export function useTripCollaboratorRealtime(tripId: number | null) {
  return useSupabaseRealtime({
    table: "trip_collaborators",
    filter: tripId ? `trip_id=eq.${tripId}` : undefined,
    onInsert: (payload) => {
      console.log("👥 New collaborator added:", payload.new);
    },
    onDelete: (payload) => {
      console.log("👥 Collaborator removed:", payload.old);
    },
  });
}

/**
 * Connection status monitoring for real-time features
 */
export function useRealtimeConnectionStatus() {
  const supabase = useSupabase();
  const statusRef = useRef<string>("CLOSED");

  useEffect(() => {
    const channel = supabase.channel("connection-status");
    
    channel.subscribe((status) => {
      statusRef.current = status;
      console.log("🔌 Realtime connection status:", status);
    });

    return () => {
      supabase.removeChannel(channel);
    };
  }, [supabase]);

  return {
    status: statusRef.current,
    isConnected: statusRef.current === "SUBSCRIBED",
  };
}