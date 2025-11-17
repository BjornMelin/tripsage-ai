/**
 * @fileoverview Chat messages slice - sessions, messages, streaming.
 *
 * Manages chat sessions, message history, streaming state, and tool calls.
 * Client-only slice - no direct Supabase clients or server logic.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  Attachment,
  ChatSession,
  Message,
  SendMessageOptions,
} from "@/lib/schemas/chat";
import { generateId, getCurrentTimestamp } from "@/lib/stores/helpers";
import { useChatMemory } from "./chat-memory";

/**
 * Chat messages state interface.
 */
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
  addMessage: (sessionId: string, message: Omit<Message, "id" | "timestamp">) => string;
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

/**
 * Chat messages store hook.
 */
export const useChatMessages = create<ChatMessagesState>()(
  persist(
    (set, get) => ({
      addMessage: (sessionId, message) => {
        const timestamp = getCurrentTimestamp();
        const messageId = generateId();

        const newMessage: Message = {
          id: messageId,
          ...message,
          timestamp,
        };

        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  messages: [...(session.messages || []), newMessage],
                  updatedAt: timestamp,
                }
              : session
          ),
        }));

        // Trigger memory sync for conversation messages
        const session = get().sessions.find((s) => s.id === sessionId);
        if (session?.userId) {
          // Trigger conversation memory storage in background
          useChatMemory
            .getState()
            .storeConversationMemory(sessionId, session.userId, [newMessage])
            .catch((error) => {
              console.warn("Memory sync failed:", error);
            });
        }

        return messageId;
      },

      addToolResult: (sessionId, messageId, callId, result) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  messages: (session.messages || []).map((message) =>
                    message.id === messageId
                      ? {
                          ...message,
                          toolCalls: (message.toolCalls || []).map((call) =>
                            call.id === callId ? { ...call, status: "completed" } : call
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
          ),
        }));
      },

      clearError: () => set({ error: null }),

      clearMessages: (sessionId) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  messages: [],
                  updatedAt: getCurrentTimestamp(),
                }
              : session
          ),
        }));
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
          currentSessionId: sessionId,
          sessions: [newSession, ...state.sessions],
        }));

        return sessionId;
      },

      get currentSession() {
        const { sessions, currentSessionId } = get();
        if (!currentSessionId) return null;
        return sessions.find((s) => s.id === currentSessionId) || null;
      },
      currentSessionId: null,

      deleteSession: (sessionId) => {
        set((state) => {
          const sessions = state.sessions.filter((s) => s.id !== sessionId);

          const currentSessionId =
            state.currentSessionId === sessionId
              ? sessions.length > 0
                ? sessions[0].id
                : null
              : state.currentSessionId;

          return { currentSessionId, sessions };
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
            currentSessionId: sessionId,
            sessions: [importedSession, ...state.sessions],
          }));

          return sessionId;
        } catch (error) {
          set({
            error:
              error instanceof Error ? error.message : "Failed to import session data",
          });
          return null;
        }
      },
      isLoading: false,
      isStreaming: false,

      renameSession: (sessionId, title) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? { ...session, title, updatedAt: getCurrentTimestamp() }
              : session
          ),
        }));
      },

      sendMessage: async (content, options = {}) => {
        const { currentSessionId, currentSession } = get();

        let sessionId = currentSessionId;
        if (!sessionId || !currentSession) {
          sessionId = get().createSession("New Conversation");
        }

        // Add user message
        get().addMessage(sessionId, {
          attachments: options.attachments?.map((file) => ({
            contentType: file.type,
            id: generateId(),
            name: file.name,
            size: file.size,
            url: URL.createObjectURL(file),
          })),
          content,
          role: "user",
        });

        set({ error: null, isLoading: true });

        try {
          // Placeholder: This will be replaced with actual API call
          // API calls should go through route handlers, not directly from slice
          await new Promise((resolve) => setTimeout(resolve, 1000));

          // Mock AI response
          get().addMessage(sessionId, {
            content: `I've received your message: "${content}". This is a placeholder response that will be replaced with actual API integration.`,
            role: "assistant",
          });

          set({ isLoading: false });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Failed to send message",
            isLoading: false,
          });

          get().addMessage(sessionId, {
            content:
              "Sorry, there was an error processing your request. Please try again.",
            role: "system",
          });
        }
      },
      sessions: [],

      setCurrentSession: (sessionId) => {
        set({ currentSessionId: sessionId });
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

        // Add user message
        get().addMessage(sessionId, {
          attachments: options.attachments?.map((file) => ({
            contentType: file.type,
            id: generateId(),
            name: file.name,
            size: file.size,
            url: URL.createObjectURL(file),
          })),
          content,
          role: "user",
        });

        // Create a placeholder message for streaming
        const assistantMessageId = get().addMessage(sessionId, {
          content: "",
          isStreaming: true,
          role: "assistant",
        });

        set({ error: null, isStreaming: true });
        abortController = new AbortController();

        try {
          // Placeholder: This will be replaced with actual streaming API call
          // Streaming should use AI SDK v6 primitives in route handlers
          let streamContent = "";
          const fullResponse =
            "This is a simulated streaming response that will be replaced with actual API integration using the Vercel AI SDK for real-time streaming of AI-generated content.";
          const words = fullResponse.split(" ");

          for (let i = 0; i < words.length; i++) {
            if (abortController?.signal.aborted) {
              break;
            }

            streamContent += (i === 0 ? "" : " ") + words[i];

            get().updateMessage(sessionId, assistantMessageId, {
              content: streamContent,
            });

            await new Promise((resolve) => setTimeout(resolve, 50));
          }

          get().updateMessage(sessionId, assistantMessageId, {
            isStreaming: false,
          });
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
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  messages: (session.messages || []).map((message) =>
                    message.id === messageId ? { ...message, ...updates } : message
                  ),
                  updatedAt: getCurrentTimestamp(),
                }
              : session
          ),
        }));
      },
    }),
    {
      name: "chat-messages-storage",
      partialize: (state) => ({
        currentSessionId: state.currentSessionId,
        sessions: state.sessions,
      }),
    }
  )
);

// Selectors
export const useCurrentSession = () => useChatMessages((state) => state.currentSession);
export const useSessions = () => useChatMessages((state) => state.sessions);
export const useIsStreaming = () => useChatMessages((state) => state.isStreaming);
export const useIsLoading = () => useChatMessages((state) => state.isLoading);
export const useChatError = () => useChatMessages((state) => state.error);
