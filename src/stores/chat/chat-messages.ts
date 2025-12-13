/**
 * @fileoverview Chat messages slice - sessions, messages, streaming.
 *
 * Manages chat sessions, message history, streaming state, and tool calls.
 * Client-only slice - no direct Supabase clients or server logic.
 */

import type { ChatSession, Message } from "@schemas/chat";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { generateId, getCurrentTimestamp } from "@/stores/helpers";

// Memory sync handled server-side via orchestrator - no client-side memory store needed

/** Chat messages state interface. */
export interface ChatMessagesState {
  // State
  sessions: ChatSession[];
  currentSessionId: string | null;
  isLoading: boolean;
  error: string | null;

  // Computed
  currentSession: ChatSession | null;

  // Session actions
  createSession: (title?: string, userId?: string, agentId?: string) => string;
  setCurrentSession: (sessionId: string) => void;
  deleteSession: (sessionId: string) => void;
  renameSession: (sessionId: string, title: string) => void;

  // Message actions
  addMessage: (sessionId: string, message: Omit<Message, "id" | "timestamp">) => string;
  updateMessage: (
    sessionId: string,
    messageId: string,
    updates: Partial<Omit<Message, "id" | "timestamp">>
  ) => void;
  clearMessages: (sessionId: string) => void;

  // Tool actions
  addToolResult: (
    sessionId: string,
    messageId: string,
    callId: string,
    result: unknown
  ) => void;

  // Utility
  clearError: () => void;
  exportSessionData: (sessionId: string) => string;
  importSessionData: (jsonData: string) => string | null;
}

// Track object URLs for attachment cleanup
const objectUrls = new Map<string, Set<string>>(); // sessionId -> Set<objectUrl>

const deriveCurrentSession = (
  sessions: ChatSession[],
  currentSessionId: string | null
): ChatSession | null => {
  if (!currentSessionId) {
    return null;
  }

  return sessions.find((session) => session.id === currentSessionId) || null;
};

/**
 * Chat messages store hook.
 */
export const useChatMessages = create<ChatMessagesState>()(
  persist(
    (set, get) => {
      return {
        addMessage: (sessionId, message) => {
          const timestamp = getCurrentTimestamp();
          const messageId = generateId();

          const newMessage: Message = {
            id: messageId,
            ...message,
            timestamp,
          };

          set((state) => {
            const sessions = state.sessions.map<ChatSession>((session) =>
              session.id === sessionId
                ? {
                    ...session,
                    messages: [...(session.messages || []), newMessage],
                    updatedAt: timestamp,
                  }
                : session
            );

            return {
              currentSession: deriveCurrentSession(sessions, state.currentSessionId),
              sessions,
            };
          });

          return messageId;
        },

        addToolResult: (sessionId, messageId, callId, result) => {
          set((state) => {
            const sessions = state.sessions.map<ChatSession>((session) =>
              session.id === sessionId
                ? {
                    ...session,
                    messages: (session.messages || []).map((message) =>
                      message.id === messageId
                        ? {
                            ...message,
                            toolCalls: (message.toolCalls || []).map((call) =>
                              call.id === callId
                                ? { ...call, status: "completed" }
                                : call
                            ),
                            toolResults: [
                              ...(message.toolResults || []),
                              { callId, result, status: "success" },
                            ],
                          }
                        : message
                    ),
                    updatedAt: getCurrentTimestamp(),
                  }
                : session
            );

            return {
              currentSession: deriveCurrentSession(sessions, state.currentSessionId),
              sessions,
            };
          });
        },

        clearError: () => set({ error: null }),

        clearMessages: (sessionId) => {
          // Revoke object URLs for this session
          const urls = objectUrls.get(sessionId);
          if (urls) {
            urls.forEach((url) => {
              URL.revokeObjectURL(url);
            });
            objectUrls.delete(sessionId);
          }

          set((state) => {
            const sessions = state.sessions.map<ChatSession>((session) =>
              session.id === sessionId
                ? {
                    ...session,
                    messages: [],
                    updatedAt: getCurrentTimestamp(),
                  }
                : session
            );

            return {
              currentSession: deriveCurrentSession(sessions, state.currentSessionId),
              sessions,
            };
          });
        },

        createSession: (title, userId, agentId) => {
          const timestamp = getCurrentTimestamp();
          const sessionId = generateId();

          const newSession: ChatSession = {
            agentId: agentId || "default-agent",
            createdAt: timestamp,
            id: sessionId,
            messages: [],
            title: title || "New Conversation",
            updatedAt: timestamp,
            userId,
          };

          set((state) => ({
            currentSession: newSession,
            currentSessionId: sessionId,
            sessions: [newSession, ...state.sessions],
          }));

          return sessionId;
        },

        currentSession: null,
        currentSessionId: null,

        deleteSession: (sessionId) => {
          // Revoke object URLs for this session
          const urls = objectUrls.get(sessionId);
          if (urls) {
            urls.forEach((url) => {
              URL.revokeObjectURL(url);
            });
            objectUrls.delete(sessionId);
          }

          set((state) => {
            const sessions = state.sessions.filter((s) => s.id !== sessionId);

            const currentSessionId =
              state.currentSessionId === sessionId
                ? sessions.length > 0
                  ? sessions[0].id
                  : null
                : state.currentSessionId;

            return {
              currentSession: deriveCurrentSession(sessions, currentSessionId),
              currentSessionId,
              sessions,
            };
          });
        },
        error: null,

        exportSessionData: (sessionId) => {
          const { sessions } = get();
          const session = sessions.find((s) => s.id === sessionId);

          if (!session) return "";

          const exportData = {
            ...session,
            messages: (session.messages || []).map((msg) => ({
              ...msg,
              attachments: msg.attachments?.map((att) => ({
                contentType: att.contentType,
                id: att.id,
                name: att.name,
                url: att.url.startsWith("blob:") ? "" : att.url,
              })),
            })),
          };

          return JSON.stringify(exportData, null, 2);
        },

        importSessionData: (jsonData) => {
          try {
            const data = JSON.parse(jsonData);

            // Basic validation
            if (
              !data.id ||
              !data.title ||
              !Array.isArray(data.messages) ||
              !data.createdAt ||
              !data.updatedAt
            ) {
              set({ error: "Invalid session data format" });
              return null;
            }

            const timestamp = getCurrentTimestamp();
            const sessionId = generateId();

            const importedSession: ChatSession = {
              ...data,
              id: sessionId,
              title: `${data.title} (Imported)`,
              updatedAt: timestamp,
            };

            set((state) => ({
              currentSession: importedSession,
              currentSessionId: sessionId,
              sessions: [importedSession, ...state.sessions],
            }));

            return sessionId;
          } catch (error) {
            set({
              error:
                error instanceof Error
                  ? error.message
                  : "Failed to import session data",
            });
            return null;
          }
        },
        isLoading: false,

        renameSession: (sessionId, title) => {
          set((state) => {
            const sessions = state.sessions.map<ChatSession>((session) =>
              session.id === sessionId
                ? { ...session, title, updatedAt: getCurrentTimestamp() }
                : session
            );

            return {
              currentSession: deriveCurrentSession(sessions, state.currentSessionId),
              sessions,
            };
          });
        },
        sessions: [],

        setCurrentSession: (sessionId) => {
          set((state) => ({
            currentSession: deriveCurrentSession(state.sessions, sessionId),
            currentSessionId: sessionId,
          }));
        },

        updateMessage: (sessionId, messageId, updates) => {
          set((state) => {
            const sessions = state.sessions.map<ChatSession>((session) =>
              session.id === sessionId
                ? {
                    ...session,
                    messages: (session.messages || []).map((message) =>
                      message.id === messageId ? { ...message, ...updates } : message
                    ),
                    updatedAt: getCurrentTimestamp(),
                  }
                : session
            );

            return {
              currentSession: deriveCurrentSession(sessions, state.currentSessionId),
              sessions,
            };
          });
        },
      };
    },
    {
      name: "chat-messages-storage",
      partialize: (state) => ({
        currentSessionId: state.currentSessionId,
        sessions: state.sessions,
      }),
    }
  )
);

let syncingCurrentSession = false;

useChatMessages.subscribe((state) => {
  if (syncingCurrentSession) {
    return;
  }

  const derivedSession = deriveCurrentSession(state.sessions, state.currentSessionId);
  if (state.currentSession === derivedSession) {
    return;
  }

  syncingCurrentSession = true;
  useChatMessages.setState({ currentSession: derivedSession });
  syncingCurrentSession = false;
});

// Selectors
export const useCurrentSession = () => useChatMessages((state) => state.currentSession);
export const useSessions = () => useChatMessages((state) => state.sessions);
export const useIsLoading = () => useChatMessages((state) => state.isLoading);
export const useChatError = () => useChatMessages((state) => state.error);
