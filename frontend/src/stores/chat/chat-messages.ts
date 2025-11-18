/**
 * @fileoverview Chat messages slice - sessions, messages, streaming.
 *
 * Manages chat sessions, message history, streaming state, and tool calls.
 * Client-only slice - no direct Supabase clients or server logic.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { sendChatMessage, streamChatMessage } from "@/lib/chat/api-client";
import type { ChatSession, Message, SendMessageOptions } from "@/lib/schemas/chat";
import { generateId, getCurrentTimestamp } from "@/lib/stores/helpers";

// Memory sync handled server-side via orchestrator - no client-side memory store needed

type AddMessageOptions = {
  syncMemory?: boolean;
};

/** Chat messages state interface. */
export interface ChatMessagesState {
  // State
  sessions: ChatSession[];
  currentSessionId: string | null;
  isLoading: boolean;
  isStreaming: boolean;
  error: string | null;

  // Computed
  currentSession: ChatSession | null;

  // Session actions
  createSession: (title?: string, userId?: string) => string;
  setCurrentSession: (sessionId: string) => void;
  deleteSession: (sessionId: string) => void;
  renameSession: (sessionId: string, title: string) => void;

  // Message actions
  addMessage: (
    sessionId: string,
    message: Omit<Message, "id" | "timestamp">,
    options?: AddMessageOptions
  ) => string;
  updateMessage: (
    sessionId: string,
    messageId: string,
    updates: Partial<Omit<Message, "id" | "timestamp">>
  ) => void;
  clearMessages: (sessionId: string) => void;

  // Streaming actions
  sendMessage: (content: string, options?: SendMessageOptions) => Promise<void>;
  streamMessage: (content: string, options?: SendMessageOptions) => Promise<void>;
  stopStreaming: () => void;

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

// Abort controller for canceling stream requests
let abortController: AbortController | null = null;

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
      const findSession = (sessionId: string) =>
        get().sessions.find((session) => session.id === sessionId);

      const storeMessageInMemory = (
        _sessionId: string,
        message: Message,
        syncMemory: boolean
      ) => {
        if (!syncMemory || message.role === "system" || message.isStreaming) {
          return;
        }
      };

      const syncSessionMemory = (sessionId: string) => {
        const session = findSession(sessionId);
        const userId = session?.userId;
        if (!userId) return;
      };

      return {
        addMessage: (sessionId, message, options) => {
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

          const shouldSyncMemory = options?.syncMemory ?? true;
          storeMessageInMemory(sessionId, newMessage, shouldSyncMemory);

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

        createSession: (title, userId) => {
          const timestamp = getCurrentTimestamp();
          const sessionId = generateId();

          const newSession: ChatSession = {
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
        isStreaming: false,

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

        sendMessage: async (content, options = {}) => {
          const { currentSessionId, currentSession } = get();

          let sessionId = currentSessionId;
          if (!sessionId || !currentSession) {
            sessionId = get().createSession("New Conversation");
          }

          const session = get().sessions.find((s) => s.id === sessionId);
          const existingMessages = session?.messages || [];

          // Add user message with attachment URL tracking
          const attachmentUrls: string[] = [];
          get().addMessage(sessionId, {
            attachments: options.attachments?.map((file) => {
              const objectUrl = URL.createObjectURL(file);
              attachmentUrls.push(objectUrl);
              // Track object URL for cleanup
              if (!objectUrls.has(sessionId)) {
                objectUrls.set(sessionId, new Set());
              }
              objectUrls.get(sessionId)?.add(objectUrl);
              return {
                contentType: file.type,
                id: generateId(),
                name: file.name,
                size: file.size,
                url: objectUrl,
              };
            }),
            content,
            role: "user",
          });

          set({ error: null, isLoading: true });

          try {
            // Call API route to send message
            const assistantMessage = await sendChatMessage(
              {
                content,
                options,
                sessionId,
              },
              existingMessages
            );

            // Add assistant response
            get().addMessage(sessionId, assistantMessage);

            syncSessionMemory(sessionId);

            set({ isLoading: false });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : "Failed to send message",
              isLoading: false,
            });

            get().addMessage(
              sessionId,
              {
                content:
                  "Sorry, there was an error processing your request. Please try again.",
                role: "system",
              },
              { syncMemory: false }
            );
          }
        },
        sessions: [],

        setCurrentSession: (sessionId) => {
          set((state) => ({
            currentSession: deriveCurrentSession(state.sessions, sessionId),
            currentSessionId: sessionId,
          }));
        },

        stopStreaming: () => {
          if (abortController) {
            abortController.abort();
            abortController = null;
            set({ isStreaming: false });
          }
        },

        streamMessage: async (content, options = {}) => {
          const { currentSessionId, currentSession } = get();

          let sessionId = currentSessionId;
          if (!sessionId || !currentSession) {
            sessionId = get().createSession("New Conversation");
          }

          const session = get().sessions.find((s) => s.id === sessionId);
          const existingMessages = session?.messages || [];

          // Add user message with attachment URL tracking
          const attachmentUrls: string[] = [];
          get().addMessage(sessionId, {
            attachments: options.attachments?.map((file) => {
              const objectUrl = URL.createObjectURL(file);
              attachmentUrls.push(objectUrl);
              // Track object URL for cleanup
              if (!objectUrls.has(sessionId)) {
                objectUrls.set(sessionId, new Set());
              }
              objectUrls.get(sessionId)?.add(objectUrl);
              return {
                contentType: file.type,
                id: generateId(),
                name: file.name,
                size: file.size,
                url: objectUrl,
              };
            }),
            content,
            role: "user",
          });

          // Create a placeholder message for streaming
          const assistantMessageId = get().addMessage(
            sessionId,
            {
              content: "",
              isStreaming: true,
              role: "assistant",
            },
            { syncMemory: false }
          );

          set({ error: null, isStreaming: true });
          abortController = new AbortController();

          try {
            let streamContent = "";

            // Call API route to stream message
            await streamChatMessage(
              {
                content,
                options,
                sessionId,
              },
              existingMessages,
              (chunk) => {
                if (abortController?.signal.aborted) {
                  return;
                }
                streamContent += chunk;
                get().updateMessage(sessionId, assistantMessageId, {
                  content: streamContent,
                });
              },
              abortController.signal
            );

            get().updateMessage(sessionId, assistantMessageId, {
              isStreaming: false,
            });

            syncSessionMemory(sessionId);
          } catch (error) {
            if (!(error instanceof DOMException && error.name === "AbortError")) {
              set({
                error:
                  error instanceof Error ? error.message : "Failed to stream message",
              });

              get().updateMessage(sessionId, assistantMessageId, {
                content:
                  "Sorry, there was an error generating the response. Please try again.",
                isStreaming: false,
              });
            }
          } finally {
            abortController = null;
            set({ isStreaming: false });
          }
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
export const useIsStreaming = () => useChatMessages((state) => state.isStreaming);
export const useIsLoading = () => useChatMessages((state) => state.isLoading);
export const useChatError = () => useChatMessages((state) => state.error);
