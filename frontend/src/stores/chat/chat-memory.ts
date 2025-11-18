/**
 * @fileoverview Chat memory slice - memory context, sync.
 *
 * Manages memory context storage, auto-sync preferences, and conversation
 * memory storage. Client-only slice - actual sync jobs stay in route handlers.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Message } from "@/lib/schemas/chat";
import { getCurrentTimestamp } from "@/lib/stores/helpers";

// Simplified memory context for chat sessions (matches chat-store usage)
type ChatMemoryContext = {
  context: string;
  score: number;
  source?: string;
};

/**
 * Chat memory state interface.
 */
export interface ChatMemoryState {
  // State
  memoryEnabled: boolean;
  autoSyncMemory: boolean;
  memoryContexts: Record<string, ChatMemoryContext>; // sessionId -> context
  lastMemorySyncs: Record<string, string>; // sessionId -> timestamp

  // Actions
  setMemoryEnabled: (enabled: boolean) => void;
  setAutoSyncMemory: (enabled: boolean) => void;
  updateSessionMemoryContext: (sessionId: string, context: ChatMemoryContext) => void;
  syncMemoryToSession: (sessionId: string, userId: string) => Promise<void>;
  storeConversationMemory: (
    sessionId: string,
    userId: string,
    messages?: Message[]
  ) => Promise<void>;
}

/**
 * Chat memory store hook.
 */
export const useChatMemory = create<ChatMemoryState>()(
  persist(
    (set, get) => ({
      autoSyncMemory: true,
      lastMemorySyncs: {},
      memoryContexts: {},
      memoryEnabled: true,

      setAutoSyncMemory: (enabled) => set({ autoSyncMemory: enabled }),

      setMemoryEnabled: (enabled) => set({ memoryEnabled: enabled }),

      storeConversationMemory: async (sessionId, userId, messages) => {
        if (!get().memoryEnabled || !get().autoSyncMemory) return;

        try {
          const messagesToStore = messages || [];
          if (messagesToStore.length === 0) return;

          // Convert messages to API format
          const conversationMessages = messagesToStore.map((msg) => ({
            content: msg.content || "",
            metadata: {
              attachments: msg.attachments,
              toolCalls: msg.toolCalls,
              toolResults: msg.toolResults,
            },
            role: msg.role,
            timestamp: msg.timestamp || new Date().toISOString(),
          }));

          // Call API route to enqueue memory sync job
          const response = await fetch("/api/memory/sync", {
            body: JSON.stringify({
              messages: conversationMessages,
              mode: "conversation",
              sessionId,
              userId,
            }),
            headers: { "Content-Type": "application/json" },
            method: "POST",
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(
              errorData.error || `Memory sync failed: ${response.status}`
            );
          }

          // Update local sync timestamp
          const timestamp = getCurrentTimestamp();
          set((state) => ({
            lastMemorySyncs: {
              ...state.lastMemorySyncs,
              [sessionId]: timestamp,
            },
          }));
        } catch (error) {
          console.error("Failed to enqueue conversation memory sync:", error);
          // Don't throw - memory sync is best-effort
        }
      },

      syncMemoryToSession: async (sessionId, userId) => {
        if (!get().memoryEnabled) return;

        try {
          // Determine sync type based on last sync time
          const lastSync = get().lastMemorySyncs[sessionId];
          const now = Date.now();
          const lastSyncTime = lastSync ? new Date(lastSync).getTime() : 0;
          const timeSinceLastSync = now - lastSyncTime;

          // If no sync in last 24 hours, do full sync; otherwise incremental
          const shouldDoFullSync = timeSinceLastSync > 24 * 60 * 60 * 1000;
          const mode = shouldDoFullSync ? "full" : "incremental";

          // Call API route to enqueue memory sync job
          const response = await fetch("/api/memory/sync", {
            body: JSON.stringify({
              mode,
              sessionId,
              userId,
            }),
            headers: { "Content-Type": "application/json" },
            method: "POST",
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(
              errorData.error || `Memory sync failed: ${response.status}`
            );
          }

          // Update local sync timestamp
          const timestamp = getCurrentTimestamp();
          set((state) => ({
            lastMemorySyncs: {
              ...state.lastMemorySyncs,
              [sessionId]: timestamp,
            },
          }));
        } catch (error) {
          console.error("Failed to enqueue memory sync:", error);
          // Don't throw - memory sync is best-effort
        }
      },

      updateSessionMemoryContext: (sessionId, context) => {
        const timestamp = getCurrentTimestamp();
        set((state) => ({
          lastMemorySyncs: {
            ...state.lastMemorySyncs,
            [sessionId]: timestamp,
          },
          memoryContexts: {
            ...state.memoryContexts,
            [sessionId]: context,
          },
        }));
      },
    }),
    {
      name: "chat-memory-storage",
      partialize: (state) => ({
        autoSyncMemory: state.autoSyncMemory,
        memoryEnabled: state.memoryEnabled,
      }),
    }
  )
);

// Selectors
export const useMemoryEnabled = () => useChatMemory((state) => state.memoryEnabled);
export const useMemoryContext = (sessionId: string) =>
  useChatMemory((state) => state.memoryContexts[sessionId]);
export const useAutoSyncMemory = () => useChatMemory((state) => state.autoSyncMemory);
export const useLastMemorySync = (sessionId: string) =>
  useChatMemory((state) => state.lastMemorySyncs[sessionId]);
