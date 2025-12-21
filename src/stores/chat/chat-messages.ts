/**
 * @fileoverview Chat messages slice - sessions, messages, streaming.
 *
 * Manages chat sessions, message history, streaming state, and tool calls.
 * Client-only slice - no direct Supabase clients or server logic.
 */

"use client";

import { type ChatSession, chatSessionSchema, type Message } from "@schemas/chat";
import { z } from "zod";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import { generateId, getCurrentTimestamp } from "@/stores/helpers";
import { withComputed } from "@/stores/middleware/computed";

// Memory sync handled server-side via orchestrator - no client-side memory store needed

const logger = createStoreLogger({ storeName: "chat-messages" });
const chatSessionImportSchema = chatSessionSchema.extend({
  agentId: z.string().default("default-agent"),
});

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

const MAX_URL_LENGTH = 2048;
const MAX_URL_DEBUG_LENGTH = 200;

type DroppedAttachmentUrlReason =
  | "empty"
  | "blob"
  | "too long"
  | "unsupported protocol"
  | "malformed";

const getAttachmentUrlDebugValue = (value: string): string => {
  const trimmed = value.trim();
  try {
    const parsed = new URL(trimmed);
    parsed.hash = "";
    parsed.search = "";
    return parsed.toString().slice(0, MAX_URL_DEBUG_LENGTH);
  } catch {
    return trimmed.slice(0, MAX_URL_DEBUG_LENGTH);
  }
};

const logDroppedAttachmentUrl = (
  value: string,
  reason: DroppedAttachmentUrlReason
): void => {
  if (process.env.NODE_ENV !== "development") return;
  try {
    console.debug(
      "[chat-messages] Dropped attachment URL",
      JSON.stringify({ reason, value: getAttachmentUrlDebugValue(value) })
    );
  } catch {
    // Ignore debug logging failures (stringify, URL parsing, etc.)
  }
};

const sanitizeExportedAttachmentUrl = (value: string): string => {
  const trimmed = value.trim();
  if (!trimmed) {
    logDroppedAttachmentUrl(value, "empty");
    return "";
  }
  if (trimmed.startsWith("blob:")) {
    logDroppedAttachmentUrl(value, "blob");
    return "";
  }
  if (trimmed.length > MAX_URL_LENGTH) {
    logDroppedAttachmentUrl(value, "too long");
    return "";
  }

  try {
    const parsed = new URL(trimmed);
    if (parsed.protocol === "https:" || parsed.protocol === "http:") {
      return trimmed;
    }
    logDroppedAttachmentUrl(value, "unsupported protocol");
  } catch {
    logDroppedAttachmentUrl(value, "malformed");
    // Ignore malformed URLs: return empty string to indicate invalid/unsupported URL.
  }

  return "";
};

/** Compute derived chat session from state. */
const computeChatState = (state: ChatMessagesState): Partial<ChatMessagesState> => {
  if (!state.currentSessionId) {
    return { currentSession: null };
  }
  const session = state.sessions.find((s) => s.id === state.currentSessionId) || null;
  return { currentSession: session };
};

/**
 * Chat messages store hook.
 */
export const useChatMessages = create<ChatMessagesState>()(
  devtools(
    persist(
      withComputed({ compute: computeChatState }, (set, get) => ({
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
            return { sessions };
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
            return { sessions };
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

            return { sessions };
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

            const newCurrentSessionId =
              state.currentSessionId === sessionId
                ? sessions.length > 0
                  ? sessions[0].id
                  : null
                : state.currentSessionId;

            return {
              currentSessionId: newCurrentSessionId,
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
                url: sanitizeExportedAttachmentUrl(att.url),
              })),
            })),
          };

          return JSON.stringify(exportData, null, 2);
        },

        importSessionData: (jsonData) => {
          try {
            const data = JSON.parse(jsonData);

            const parsed = chatSessionImportSchema.safeParse(data);
            if (!parsed.success) {
              const details =
                typeof data === "object" && data !== null
                  ? {
                      error: parsed.error,
                      payloadKeys: Object.keys(data as Record<string, unknown>),
                    }
                  : { error: parsed.error, payloadType: typeof data };
              logger.error("Invalid imported session data format", details);
              set({ error: "Invalid session data format" });
              return null;
            }

            const timestamp = getCurrentTimestamp();
            const sessionId = generateId();

            const importedSession: ChatSession = {
              ...parsed.data,
              id: sessionId,
              title: `${parsed.data.title ?? "Imported Session"} (Imported)`,
              updatedAt: timestamp,
            };

            set((state) => ({
              currentSessionId: sessionId,
              sessions: [importedSession, ...state.sessions],
            }));

            return sessionId;
          } catch (error) {
            logger.error("Failed to import session data", { error });
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
            return { sessions };
          });
        },
        sessions: [],

        setCurrentSession: (currentSessionId) => set({ currentSessionId }),

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
            return { sessions };
          });
        },
      })),
      {
        name: "chat-messages-storage",
        partialize: (state) => ({
          currentSessionId: state.currentSessionId,
          sessions: state.sessions.map((session) => ({
            ...session,
            messages: (session.messages || []).map((message) => ({
              ...message,
              attachments: message.attachments?.map((attachment) => ({
                ...attachment,
                url: sanitizeExportedAttachmentUrl(attachment.url),
              })),
            })),
          })),
        }),
      }
    ),
    { name: "ChatMessages" }
  )
);

// Selectors
export const useCurrentSession = () => useChatMessages((state) => state.currentSession);
export const useSessions = () => useChatMessages((state) => state.sessions);
export const useIsLoading = () => useChatMessages((state) => state.isLoading);
export const useChatError = () => useChatMessages((state) => state.error);
