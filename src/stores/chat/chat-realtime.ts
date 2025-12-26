/**
 * @fileoverview Chat realtime slice - WebSocket, agent status, typing.
 */

"use client";

import type { Message } from "@schemas/chat";
import type {
  AgentStatusBroadcastPayload,
  ChatMessageBroadcastPayload,
  ChatTypingBroadcastPayload,
  ConnectionStatus,
} from "@schemas/realtime";
import { CONNECTION_STATUS_SCHEMA } from "@schemas/realtime";
import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import { getCurrentTimestamp } from "@/stores/helpers";

const logger = createStoreLogger({ storeName: "chat-realtime" });
const TYPING_TIMEOUT_MS = 3000;
const typingTimeouts = new Map<string, ReturnType<typeof setTimeout>>();

/**
 * Chat realtime state interface.
 */
export interface ChatRealtimeState {
  // State
  connectionStatus: ConnectionStatus;
  isRealtimeEnabled: boolean;
  typingUsers: Record<string, { userId: string; username?: string; timestamp: string }>;
  pendingMessages: Message[];
  agentStatuses: Record<string, AgentStatusBroadcastPayload>; // sessionId -> status

  // Connection actions
  setChatConnectionStatus: (status: ConnectionStatus) => void;
  setRealtimeEnabled: (enabled: boolean) => void;
  resetRealtimeState: () => void;

  // Typing actions
  setUserTyping: (sessionId: string, userId: string, username?: string) => void;
  removeUserTyping: (sessionId: string, userId: string) => void;
  clearTypingUsers: (sessionId: string) => void;

  // Message queue
  addPendingMessage: (message: Message) => void;
  removePendingMessage: (messageId: string) => void;

  // Agent status
  updateAgentStatus: (
    sessionId: string,
    status: Partial<AgentStatusBroadcastPayload>
  ) => void;

  // Broadcast handlers
  handleRealtimeMessage: (
    sessionId: string,
    payload: ChatMessageBroadcastPayload
  ) => void;
  handleTypingUpdate: (sessionId: string, payload: ChatTypingBroadcastPayload) => void;
  handleAgentStatusUpdate: (
    sessionId: string,
    payload: AgentStatusBroadcastPayload
  ) => void;
}

/**
 * Chat realtime store hook.
 */
export const useChatRealtime = create<ChatRealtimeState>()(
  devtools(
    (set, get) => ({
      addPendingMessage: (message) => {
        set((state) => ({
          pendingMessages: [...state.pendingMessages, message],
        }));
      },
      agentStatuses: {},

      clearTypingUsers: (sessionId) => {
        set((state) => {
          const newTypingUsers = { ...state.typingUsers };
          for (const key of Object.keys(newTypingUsers)) {
            if (key.startsWith(`${sessionId}_`)) {
              const existingTimeout = typingTimeouts.get(key);
              if (existingTimeout) {
                clearTimeout(existingTimeout);
                typingTimeouts.delete(key);
              }
              delete newTypingUsers[key];
            }
          }
          return { typingUsers: newTypingUsers };
        });
      },
      connectionStatus: "disconnected",

      handleAgentStatusUpdate: (sessionId, payload) => {
        get().updateAgentStatus(sessionId, {
          currentTask: payload.currentTask,
          isActive: payload.isActive,
          progress: payload.progress,
          statusMessage: payload.statusMessage,
        });
      },

      handleRealtimeMessage: () => {
        // Intentionally a no-op: message addition is handled by the calling hook via the
        // messages slice (this slice only tracks realtime connection state).
      },

      handleTypingUpdate: (sessionId, payload) => {
        if (!payload.userId) {
          return;
        }

        if (payload.isTyping) {
          get().setUserTyping(sessionId, payload.userId, payload.username);
        } else {
          get().removeUserTyping(sessionId, payload.userId);
        }
      },
      isRealtimeEnabled: true,
      pendingMessages: [],

      removePendingMessage: (messageId) => {
        set((state) => ({
          pendingMessages: state.pendingMessages.filter((m) => m.id !== messageId),
        }));
      },

      removeUserTyping: (sessionId, userId) => {
        const key = `${sessionId}_${userId}`;
        const existingTimeout = typingTimeouts.get(key);
        if (existingTimeout) {
          clearTimeout(existingTimeout);
          typingTimeouts.delete(key);
        }

        set((state) => {
          const newTypingUsers = { ...state.typingUsers };
          delete newTypingUsers[key];
          return { typingUsers: newTypingUsers };
        });
      },

      resetRealtimeState: () =>
        set(() => {
          for (const timeout of typingTimeouts.values()) {
            clearTimeout(timeout);
          }
          typingTimeouts.clear();

          return {
            agentStatuses: {},
            connectionStatus: "disconnected",
            pendingMessages: [],
            typingUsers: {},
          };
        }),

      setChatConnectionStatus: (status) => {
        // Validate status matches schema
        const parsed = CONNECTION_STATUS_SCHEMA.safeParse(status);
        if (parsed.success) return set({ connectionStatus: parsed.data });

        logger.error("Invalid connection status update dropped", {
          error: parsed.error,
          status,
        });
        return;
      },

      setRealtimeEnabled: (enabled) => {
        if (!enabled) {
          set(() => {
            for (const timeout of typingTimeouts.values()) {
              clearTimeout(timeout);
            }
            typingTimeouts.clear();

            return {
              agentStatuses: {},
              connectionStatus: "disconnected",
              isRealtimeEnabled: false,
              pendingMessages: [],
              typingUsers: {},
            };
          });
          return;
        }
        set({ isRealtimeEnabled: true });
      },

      setUserTyping: (sessionId, userId, username) => {
        const key = `${sessionId}_${userId}`;
        const existingTimeout = typingTimeouts.get(key);
        if (existingTimeout) {
          clearTimeout(existingTimeout);
          typingTimeouts.delete(key);
        }

        const timestamp = getCurrentTimestamp();
        set((state) => ({
          typingUsers: {
            ...state.typingUsers,
            [key]: {
              timestamp,
              userId,
              username,
            },
          },
        }));

        // Auto-remove after 3 seconds
        const timeout = setTimeout(() => {
          typingTimeouts.delete(key);
          get().removeUserTyping(sessionId, userId);
        }, TYPING_TIMEOUT_MS);
        typingTimeouts.set(key, timeout);
      },
      typingUsers: {},

      updateAgentStatus: (sessionId, status) => {
        set((state) => {
          const existing = state.agentStatuses[sessionId] || {
            isActive: false,
            progress: 0,
          };
          return {
            agentStatuses: {
              ...state.agentStatuses,
              [sessionId]: {
                ...existing,
                ...status,
              },
            },
          };
        });
      },
    }),
    { name: "chat-realtime" }
  )
);

// Selectors
export const useConnectionStatus = () =>
  useChatRealtime((state) => state.connectionStatus);
export const useAgentStatus = (sessionId: string) =>
  useChatRealtime((state) => state.agentStatuses[sessionId]);
export const useTypingUsers = (sessionId: string) =>
  useChatRealtime((state) => {
    const users: Array<{ userId: string; username?: string; timestamp: string }> = [];
    for (const [key, value] of Object.entries(state.typingUsers)) {
      if (key.startsWith(`${sessionId}_`)) {
        users.push(value);
      }
    }
    return users;
  });
export const usePendingMessages = () =>
  useChatRealtime((state) => state.pendingMessages);
export const useIsRealtimeEnabled = () =>
  useChatRealtime((state) => state.isRealtimeEnabled);
