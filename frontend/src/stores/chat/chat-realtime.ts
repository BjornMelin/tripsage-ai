/**
 * @fileoverview Chat realtime slice - WebSocket, agent status, typing.
 *
 * Manages real-time connection status, typing indicators, agent status updates,
 * and pending message queues. Client-only slice - actual channel management
 * stays in hooks/route handlers.
 */

import type {
  AgentStatusBroadcastPayload,
  ChatMessageBroadcastPayload,
  ChatTypingBroadcastPayload,
  ConnectionStatus,
  Message,
} from "@domain/types";
import { CONNECTION_STATUS_SCHEMA } from "@schemas/realtime";
import { create } from "zustand";
import { getCurrentTimestamp } from "@/lib/stores/helpers";

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
export const useChatRealtime = create<ChatRealtimeState>()((set, get) => ({
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

  handleRealtimeMessage: (_sessionId, payload) => {
    // This handler is called by hooks that manage actual Supabase channels
    // The slice just tracks state - actual message addition goes through messages slice
    if (!payload.content) {
      return;
    }
    // Note: Actual message addition should be handled by the calling hook
    // which will use the messages slice's addMessage action
  },

  handleTypingUpdate: (sessionId, payload) => {
    if (!payload.userId) {
      return;
    }

    if (payload.isTyping) {
      get().setUserTyping(sessionId, payload.userId);
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
    set((state) => {
      const newTypingUsers = { ...state.typingUsers };
      delete newTypingUsers[`${sessionId}_${userId}`];
      return { typingUsers: newTypingUsers };
    });
  },

  resetRealtimeState: () =>
    set({
      connectionStatus: "disconnected",
      pendingMessages: [],
      typingUsers: {},
    }),

  setChatConnectionStatus: (status) => {
    // Validate status matches schema
    const parsed = CONNECTION_STATUS_SCHEMA.safeParse(status);
    if (parsed.success) {
      set({ connectionStatus: parsed.data });
    }
  },

  setRealtimeEnabled: (enabled) => {
    set({ isRealtimeEnabled: enabled });
    if (!enabled) {
      get().resetRealtimeState();
    }
  },

  setUserTyping: (sessionId, userId, username) => {
    const timestamp = getCurrentTimestamp();
    set((state) => ({
      typingUsers: {
        ...state.typingUsers,
        [`${sessionId}_${userId}`]: {
          timestamp,
          userId,
          username,
        },
      },
    }));

    // Auto-remove after 3 seconds
    setTimeout(() => {
      get().removeUserTyping(sessionId, userId);
    }, 3000);
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
}));

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
