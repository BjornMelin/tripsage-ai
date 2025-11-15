/**
 * @fileoverview Chat store implementation using Zustand.
 *
 * State management for chat functionality including sessions,
 * messages, real-time connections, memory integration, and agent status tracking.
 * Provides persistent storage, optimistic updates, and WebSocket integration
 * for the TripSage AI assistant platform.
 */

import { z } from "zod";
import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Connection status enumeration for real-time communications.
 *
 * Defines the possible states of WebSocket/realtime connections in the chat system.
 * Used for UI state management and connection status indicators.
 */
export enum ConnectionStatus {
  Connecting = "connecting",
  Connected = "connected",
  Disconnected = "disconnected",
  Reconnecting = "reconnecting",
  Error = "error",
}

import type {
  ChatMessageBroadcastPayload,
  ChatTypingBroadcastPayload,
} from "@/hooks/use-websocket-chat";
import type { ConversationMessage, MemoryContextResponse } from "@/lib/schemas/memory";

/**
 * Message interface with support for tool calls and attachments.
 *
 * Represents a chat message in the conversation with support for advanced
 * features like tool calling, file attachments, and streaming responses.
 */
export interface Message {
  /** Unique identifier for the message */
  id: string;
  /** Role of the message sender */
  role: "user" | "assistant" | "system";
  /** Text content of the message */
  content: string;
  /** ISO timestamp when the message was created */
  timestamp: string;

  /** Optional tool calls initiated by the assistant */
  toolCalls?: ToolCall[];
  /** Optional results from executed tool calls */
  toolResults?: ToolResult[];
  /** Optional file attachments */
  attachments?: Attachment[];
  /** Whether the message is currently being streamed */
  isStreaming?: boolean;
}

/**
 * Tool call interface for AI function calling.
 *
 * Represents a function call initiated by an AI assistant, including
 * the function name, arguments, and execution state.
 */
export interface ToolCall {
  /** Unique identifier for the tool call */
  id: string;
  /** Name of the function being called */
  name: string;
  /** Arguments passed to the function */
  arguments: Record<string, unknown>;
  /** Current state of the tool call execution */
  state: "call" | "partial-call" | "result";
}

/**
 * Tool result interface for function call responses.
 *
 * Represents the result of executing a tool call, linking back to the
 * original call and containing the execution outcome.
 */
export interface ToolResult {
  /** ID of the tool call this result corresponds to */
  callId: string;
  /** The result data from the tool execution */
  result: unknown;
}

/**
 * Attachment interface for file uploads.
 *
 * Represents a file attachment in a chat message with metadata
 * for display and processing.
 */
export interface Attachment {
  /** Unique identifier for the attachment */
  id: string;
  /** URL or data URL of the attachment */
  url: string;
  /** Optional display name for the attachment */
  name?: string;
  /** MIME content type of the attachment */
  contentType?: string;
  /** File size in bytes */
  size?: number;
}

/**
 * Chat session interface for conversation management.
 *
 * Represents a complete chat conversation session with messages, metadata,
 * agent status, and memory integration for persistent conversations.
 */
export interface ChatSession {
  /** Unique identifier for the chat session */
  id: string;
  /** Display title for the conversation */
  title: string;
  /** Array of messages in the conversation */
  messages: Message[];
  /** ISO timestamp when the session was created */
  createdAt: string;
  /** ISO timestamp when the session was last updated */
  updatedAt: string;
  /** Current status of the AI agent for this session */
  agentStatus?: AgentStatus;

  /** Memory context for conversation continuity */
  memoryContext?: MemoryContextResponse;
  /** User ID associated with the session */
  userId?: string;
  /** Last time memory was synchronized */
  lastMemorySync?: string;
}

/**
 * Agent status interface for AI assistant state tracking.
 *
 * Tracks the current operational status of AI agents including activity state,
 * current tasks, progress indicators, and status messages.
 */
export interface AgentStatus {
  /** Whether the agent is currently active/processing */
  isActive: boolean;
  /** Description of the current task being performed */
  currentTask?: string;
  /** Progress percentage (0-100) of current task */
  progress: number;
  /** Human-readable status message */
  statusMessage?: string;
}

/**
 * Options for sending chat messages.
 *
 * Configuration options for message sending including file attachments,
 * system prompts, AI parameters, and tool availability.
 */
export interface SendMessageOptions {
  /** Optional file attachments to include with the message */
  attachments?: File[];
  /** Custom system prompt to override defaults */
  systemPrompt?: string;
  /** AI temperature parameter for response creativity */
  temperature?: number;
  /** Available tools/functions for the AI to use */
  tools?: Record<string, unknown>[];
}

/**
 * Agent status update payload from Supabase Realtime broadcast.
 */
export interface AgentStatusBroadcastPayload {
  /** Whether the agent is currently active. */
  isActive: boolean;
  /** Current task description. */
  currentTask?: string;
  /** Progress percentage of current task (0-100). */
  progress: number;
  /** Human-readable status message. */
  statusMessage?: string;
}

/**
 * Internal chat store state interface.
 *
 * Defines the complete state structure for the chat store including sessions,
 * real-time connection status, memory integration, and all action handlers.
 * Used internally by Zustand for type-safe state management.
 */
export interface ChatState {
  sessions: ChatSession[];
  currentSessionId: string | null;
  isLoading: boolean;
  isStreaming: boolean;
  error: string | null;

  // Computed
  currentSession: ChatSession | null;

  // Memory integration
  memoryEnabled: boolean;
  autoSyncMemory: boolean;

  // Realtime integration state (hooks own connections; store tracks status only).
  connectionStatus: ConnectionStatus;
  isRealtimeEnabled: boolean;
  typingUsers: Record<string, { userId: string; username?: string; timestamp: string }>;
  pendingMessages: Message[];

  // Actions
  createSession: (title?: string, userId?: string) => string;
  setCurrentSession: (sessionId: string) => void;
  deleteSession: (sessionId: string) => void;
  renameSession: (sessionId: string, title: string) => void;
  addMessage: (sessionId: string, message: Omit<Message, "id" | "timestamp">) => string;
  updateMessage: (
    sessionId: string,
    messageId: string,
    updates: Partial<Omit<Message, "id" | "timestamp">>
  ) => void;
  sendMessage: (content: string, options?: SendMessageOptions) => Promise<void>;
  streamMessage: (content: string, options?: SendMessageOptions) => Promise<void>;
  stopStreaming: () => void;
  addToolResult: (
    sessionId: string,
    messageId: string,
    callId: string,
    result: unknown
  ) => void;
  updateAgentStatus: (sessionId: string, status: Partial<AgentStatus>) => void;
  clearMessages: (sessionId: string) => void;
  clearError: () => void;
  exportSessionData: (sessionId: string) => string;
  importSessionData: (jsonData: string) => string | null;

  // Memory actions
  updateSessionMemoryContext: (
    sessionId: string,
    memoryContext: MemoryContextResponse
  ) => void;
  syncMemoryToSession: (sessionId: string) => Promise<void>;
  storeConversationMemory: (sessionId: string, messages?: Message[]) => Promise<void>;
  setMemoryEnabled: (enabled: boolean) => void;
  setAutoSyncMemory: (enabled: boolean) => void;

  // Realtime actions (hook-driven; hooks own connections)
  setChatConnectionStatus: (status: ConnectionStatus) => void;
  setRealtimeEnabled: (enabled: boolean) => void;
  handleRealtimeMessage: (
    sessionId: string,
    payload: ChatMessageBroadcastPayload
  ) => void;
  handleAgentStatusUpdate: (
    sessionId: string,
    payload: AgentStatusBroadcastPayload
  ) => void;
  handleTypingUpdate: (sessionId: string, payload: ChatTypingBroadcastPayload) => void;
  setUserTyping: (sessionId: string, userId: string, username?: string) => void;
  removeUserTyping: (sessionId: string, userId: string) => void;
  clearTypingUsers: (sessionId: string) => void;
  addPendingMessage: (message: Message) => void;
  removePendingMessage: (messageId: string) => void;
  resetRealtimeState: () => void;
}

// Zod schema for session data validation when importing
const SESSION_DATA_SCHEMA = z.object({
  createdAt: z.string(),
  id: z.string(),
  messages: z.array(
    z.object({
      attachments: z
        .array(
          z.object({
            contentType: z.string().optional(),
            id: z.string(),
            name: z.string().optional(),
            url: z.string(),
          })
        )
        .optional(),
      content: z.string(),
      id: z.string(),
      role: z.enum(["user", "assistant", "system"]),
      timestamp: z.string(),
      toolCalls: z
        .array(
          z.object({
            arguments: z.record(z.string(), z.unknown()),
            id: z.string(),
            name: z.string(),
            state: z.enum(["call", "partial-call", "result"]),
          })
        )
        .optional(),
    })
  ),
  title: z.string(),
  updatedAt: z.string(),
});

// Abort controller for canceling stream requests
let abortController: AbortController | null = null;

/**
 * Zustand store hook for comprehensive chat state management.
 *
 * Provides centralized state management for chat functionality including:
 * - Session management (create, update, delete conversations)
 * - Message handling with optimistic updates and streaming
 * - Real-time WebSocket integration with Supabase Realtime
 * - Agent status tracking and progress monitoring
 * - Memory integration for conversation continuity
 * - Persistent storage with Zustand persist middleware
 *
 * Features optimistic UI updates, automatic reconnection, typing indicators,
 * and comprehensive error handling for robust chat experiences.
 *
 * @returns The chat store state and actions
 *
 * @example
 * ```typescript
 * const {
 *   sessions,
 *   currentSession,
 *   sendMessage,
 *   createSession,
 *   setChatConnectionStatus
 * } = useChatStore();
 * ```
 */
export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      /** Adds a new message to the specified chat session. */
      addMessage: (sessionId, message) => {
        const timestamp = new Date().toISOString();
        const messageId = Date.now().toString();

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
                  messages: [...session.messages, newMessage],
                  updatedAt: timestamp,
                }
              : session
          ),
        }));

        return messageId;
      },

      /** Adds a message to the pending messages queue. */
      addPendingMessage: (message) => {
        set((state) => ({
          pendingMessages: [...state.pendingMessages, message],
        }));
      },

      /** Adds a tool execution result to the specified message. */
      addToolResult: (sessionId, messageId, callId, result) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  messages: session.messages.map((message) =>
                    message.id === messageId
                      ? {
                          ...message,
                          toolCalls: (message.toolCalls || []).map((call) =>
                            call.id === callId ? { ...call, state: "result" } : call
                          ),
                          toolResults: [
                            ...(message.toolResults || []),
                            { callId, result },
                          ],
                        }
                      : message
                  ),
                  updatedAt: new Date().toISOString(),
                }
              : session
          ),
        }));
      },
      autoSyncMemory: true,

      /** Clears the current error state. */
      clearError: () => set({ error: null }),

      /** Removes all messages from the specified chat session. */
      clearMessages: (sessionId) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  messages: [],
                  updatedAt: new Date().toISOString(),
                }
              : session
          ),
        }));
      },

      /** Clears all typing indicators for the specified session. */
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
      connectionStatus: ConnectionStatus.Disconnected,

      /** Creates a new chat session with the given title and user ID. */
      createSession: (title, userId) => {
        const timestamp = new Date().toISOString();
        const sessionId = Date.now().toString();

        const newSession: ChatSession = {
          agentStatus: {
            isActive: false,
            progress: 0,
          },
          createdAt: timestamp,
          id: sessionId,
          lastMemorySync: undefined,
          memoryContext: undefined,
          messages: [],
          title: title || "New Conversation",
          updatedAt: timestamp,
          userId: userId,
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
        return sessions.find((session) => session.id === currentSessionId) || null;
      },
      currentSessionId: null,

      /** Deletes the specified chat session. */
      deleteSession: (sessionId) => {
        set((state) => {
          const sessions = state.sessions.filter((session) => session.id !== sessionId);

          // If we're deleting the current session, select the first available or null
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

      /** Exports session data as a JSON string for the specified session. */
      exportSessionData: (sessionId) => {
        const { sessions } = get();
        const session = sessions.find((s) => s.id === sessionId);

        if (!session) return "";

        // Create a clean copy of the session for export
        const exportData = {
          ...session,
          messages: session.messages.map((msg) => ({
            ...msg,
            // Clean up any browser-specific or non-serializable data
            attachments: msg.attachments?.map((att) => ({
              contentType: att.contentType,
              id: att.id,
              name: att.name,
              url: att.url.startsWith("blob:") ? "" : att.url, // Don't export blob URLs
            })),
          })),
        };

        return JSON.stringify(exportData, null, 2);
      },

      /** Updates agent status from realtime broadcast payload. */
      handleAgentStatusUpdate: (sessionId, payload) => {
        const { currentSessionId } = get();
        if (!currentSessionId || sessionId !== currentSessionId) return;

        get().updateAgentStatus(currentSessionId, {
          currentTask: payload.currentTask,
          isActive: payload.isActive,
          progress: payload.progress,
          statusMessage: payload.statusMessage,
        });
      },

      /** Handles incoming realtime message broadcast. */
      handleRealtimeMessage: (sessionId, payload) => {
        const { currentSessionId } = get();
        if (!currentSessionId || sessionId !== currentSessionId) return;

        if (!payload.content) {
          return;
        }

        // Add message from Supabase broadcast payload
        get().addMessage(currentSessionId, {
          content: payload.content,
          role: (payload.sender?.id === get().currentSession?.userId
            ? "user"
            : "assistant") as "user" | "assistant" | "system",
        });
      },

      /** Updates typing indicators from realtime broadcast. */
      handleTypingUpdate: (sessionId, payload) => {
        const { currentSessionId } = get();
        if (!currentSessionId || sessionId !== currentSessionId) return;

        if (!payload.userId) {
          return;
        }

        if (payload.isTyping) {
          get().setUserTyping(sessionId, payload.userId);
        } else {
          get().removeUserTyping(sessionId, payload.userId);
        }
      },

      /** Imports session data from a JSON string. */
      importSessionData: (jsonData) => {
        try {
          const data = JSON.parse(jsonData);

          // Validate the data structure
          const result = SESSION_DATA_SCHEMA.safeParse(data);
          if (!result.success) {
            set({ error: "Invalid session data format" });
            return null;
          }

          const timestamp = new Date().toISOString();
          const sessionId = Date.now().toString();

          // Create a new session with the imported data
          const importedSession: ChatSession = {
            ...data,
            id: sessionId, // Generate a new ID for this session
            messages: data.messages,
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
      isRealtimeEnabled: true,
      isStreaming: false,

      // Memory integration defaults
      memoryEnabled: true,
      pendingMessages: [],

      /** Removes a message from the pending messages queue. */
      removePendingMessage: (messageId) => {
        set((state) => ({
          pendingMessages: state.pendingMessages.filter((m) => m.id !== messageId),
        }));
      },

      /** Removes typing indicator for the specified user. */
      removeUserTyping: (sessionId, userId) => {
        set((state) => {
          const newTypingUsers = { ...state.typingUsers };
          delete newTypingUsers[`${sessionId}_${userId}`];
          return { typingUsers: newTypingUsers };
        });
      },

      /** Renames the specified chat session. */
      renameSession: (sessionId, title) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? { ...session, title, updatedAt: new Date().toISOString() }
              : session
          ),
        }));
      },

      /** Resets all realtime connection state. */
      resetRealtimeState: () => {
        set({
          connectionStatus: ConnectionStatus.Disconnected,
          pendingMessages: [],
          typingUsers: {},
        });
      },

      /** Sends a message and simulates AI response (placeholder implementation). */
      sendMessage: async (content, options = {}) => {
        const { currentSessionId, currentSession } = get();

        // Create a new session if none exists
        let sessionId = currentSessionId;
        if (!sessionId || !currentSession) {
          sessionId = get().createSession("New Conversation");
        }

        // Add user message
        get().addMessage(sessionId, {
          attachments: options.attachments?.map((file) => ({
            contentType: file.type,
            id: Date.now().toString(),
            name: file.name,
            size: file.size,
            url: URL.createObjectURL(file),
          })),
          content,
          role: "user",
        });

        set({ error: null, isLoading: true });

        // Final-Only: No direct socket send from the store; rely on HTTP or hooks.

        try {
          // Update agent status to show it's processing
          get().updateAgentStatus(sessionId, {
            currentTask: "Processing your request",
            isActive: true,
            progress: 30,
            statusMessage: "Analyzing your query...",
          });

          // This will be replaced with actual API call
          await new Promise((resolve) => setTimeout(resolve, 1000));

          // Mock AI response
          get().addMessage(sessionId, {
            content: `I've received your message: "${content}". This is a placeholder response from the AI assistant that will be replaced with the actual API integration.`,
            role: "assistant",
          });

          // Update agent status to show completion
          get().updateAgentStatus(sessionId, {
            isActive: false,
            progress: 100,
            statusMessage: "Response complete",
          });

          set({ isLoading: false });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Failed to send message",
            isLoading: false,
          });

          // Update agent status to show error
          get().updateAgentStatus(sessionId, {
            isActive: false,
            progress: 0,
            statusMessage: "Error processing request",
          });

          // Add system error message
          get().addMessage(sessionId, {
            content:
              "Sorry, there was an error processing your request. Please try again.",
            role: "system",
          });
        }
      },
      sessions: [],

      /** Enables or disables automatic memory synchronization. */
      setAutoSyncMemory: (enabled) => {
        set({ autoSyncMemory: enabled });
      },

      // Realtime actions (hook-driven; hooks own connections)
      /** Updates the realtime connection status. */
      setChatConnectionStatus: (status) => {
        set({ connectionStatus: status });
      },

      /** Sets the currently active chat session. */
      setCurrentSession: (sessionId) => {
        set({ currentSessionId: sessionId });
      },

      /** Enables or disables memory integration. */
      setMemoryEnabled: (enabled) => {
        set({ memoryEnabled: enabled });
      },

      /** Enables or disables realtime functionality. */
      setRealtimeEnabled: (enabled) => {
        set({ isRealtimeEnabled: enabled });

        if (!enabled) {
          get().resetRealtimeState();
        }
      },

      /** Sets typing indicator for the specified user. */
      setUserTyping: (sessionId, userId, username) => {
        set((state) => ({
          typingUsers: {
            ...state.typingUsers,
            [`${sessionId}_${userId}`]: {
              timestamp: new Date().toISOString(),
              userId,
              username,
            },
          },
        }));

        // Auto-remove typing indicator after 3 seconds
        setTimeout(() => {
          get().removeUserTyping(sessionId, userId);
        }, 3000);
      },

      /** Stops the current streaming response. */
      stopStreaming: () => {
        if (abortController) {
          abortController.abort();
          abortController = null;
          set({ isStreaming: false });

          // Update agent status
          const { currentSessionId } = get();
          if (currentSessionId) {
            get().updateAgentStatus(currentSessionId, {
              isActive: false,
              progress: 0,
              statusMessage: "Response generation stopped",
            });
          }
        }
      },

      /** Stores conversation messages to memory (placeholder implementation). */
      storeConversationMemory: async (sessionId, messages) => {
        const session = get().sessions.find((s) => s.id === sessionId);
        if (!session?.userId || !get().memoryEnabled || !get().autoSyncMemory) return;

        try {
          const messagesToStore = messages || session.messages;

          // Convert messages to conversation format
          const conversationMessages: ConversationMessage[] = messagesToStore.map(
            (msg) => ({
              content: msg.content,
              metadata: {
                attachments: msg.attachments,
                toolCalls: msg.toolCalls,
                toolResults: msg.toolResults,
              },
              role: msg.role,
              timestamp: msg.timestamp,
            })
          );

          // Import memory hooks here to avoid circular dependencies
          const { useAddConversationMemory: _useAddConversationMemory } = await import(
            "@/hooks/use-memory"
          );

          // Note: This would typically be handled by the component using the hook
          // This is a placeholder for the actual implementation
          console.log(
            "Would store conversation memory for session:",
            sessionId,
            "messages:",
            conversationMessages.length
          );
        } catch (error) {
          console.error("Failed to store conversation memory:", error);
        }
      },

      /** Streams a message with simulated AI response (placeholder implementation). */
      streamMessage: async (content, options = {}) => {
        const { currentSessionId, currentSession } = get();

        // Create a new session if none exists
        let sessionId = currentSessionId;
        if (!sessionId || !currentSession) {
          sessionId = get().createSession("New Conversation");
        }

        // Add user message
        get().addMessage(sessionId, {
          attachments: options.attachments?.map((file) => ({
            contentType: file.type,
            id: Date.now().toString(),
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

        // Set streaming state and create abort controller
        set({ error: null, isStreaming: true });
        abortController = new AbortController();

        // Update agent status
        get().updateAgentStatus(sessionId, {
          currentTask: "Generating response",
          isActive: true,
          progress: 10,
          statusMessage: "Starting response generation...",
        });

        try {
          // Simulate streaming response for now
          let streamContent = "";
          const fullResponse =
            "This is a simulated streaming response that will be replaced with actual API integration using the Vercel AI SDK for real-time streaming of AI-generated content. The streaming functionality will provide a more natural and engaging user experience.";
          const words = fullResponse.split(" ");

          for (let i = 0; i < words.length; i++) {
            if (abortController?.signal.aborted) {
              break;
            }

            streamContent += (i === 0 ? "" : " ") + words[i];

            // Update the message content with the streamed chunk
            get().updateMessage(sessionId, assistantMessageId, {
              content: streamContent,
            });

            // Update agent status progress
            get().updateAgentStatus(sessionId, {
              progress: Math.min(10 + Math.floor((i / words.length) * 90), 100),
              statusMessage: "Generating response...",
            });

            // Delay to simulate streaming
            await new Promise((resolve) => setTimeout(resolve, 50));
          }

          // Mark streaming as complete
          get().updateMessage(sessionId, assistantMessageId, {
            isStreaming: false,
          });

          // Update agent status to show completion
          get().updateAgentStatus(sessionId, {
            isActive: false,
            progress: 100,
            statusMessage: "Response complete",
          });
        } catch (error) {
          if (!(error instanceof DOMException && error.name === "AbortError")) {
            set({
              error:
                error instanceof Error ? error.message : "Failed to stream message",
            });

            // Add system error message
            get().updateMessage(sessionId, assistantMessageId, {
              content:
                "Sorry, there was an error generating the response. Please try again.",
              isStreaming: false,
            });

            // Update agent status to show error
            get().updateAgentStatus(sessionId, {
              isActive: false,
              progress: 0,
              statusMessage: "Error generating response",
            });
          }
        } finally {
          abortController = null;
          set({ isStreaming: false });
        }
      },

      /** Syncs memory context to the specified session (placeholder implementation). */
      syncMemoryToSession: async (sessionId) => {
        const session = get().sessions.find((s) => s.id === sessionId);
        if (!session?.userId || !get().memoryEnabled) return;

        try {
          // Import memory hooks here to avoid circular dependencies
          const { useMemoryContext: _useMemoryContext } = await import(
            "@/hooks/use-memory"
          );

          // Note: This would typically be handled by the component using the hook
          // This is a placeholder for the actual implementation
          console.log("Memory sync would fetch context for user:", session.userId);
        } catch (error) {
          console.error("Failed to sync memory to session:", error);
          set({ error: "Failed to sync memory context" });
        }
      },
      typingUsers: {},

      /** Updates agent status for the specified session. */
      updateAgentStatus: (sessionId, status) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  agentStatus: {
                    ...(session.agentStatus || {
                      isActive: false,
                      progress: 0,
                    }),
                    ...status,
                  },
                }
              : session
          ),
        }));
      },

      /** Updates the specified message in a session. */
      updateMessage: (sessionId, messageId, updates) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  messages: session.messages.map((message) =>
                    message.id === messageId ? { ...message, ...updates } : message
                  ),
                  updatedAt: new Date().toISOString(),
                }
              : session
          ),
        }));
      },

      // Memory actions
      /** Updates memory context for the specified session. */
      updateSessionMemoryContext: (sessionId, memoryContext) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  lastMemorySync: new Date().toISOString(),
                  memoryContext,
                  updatedAt: new Date().toISOString(),
                }
              : session
          ),
        }));
      },
    }),
    {
      name: "chat-storage",
      partialize: (state) => ({
        autoSyncMemory: state.autoSyncMemory,
        currentSessionId: state.currentSessionId,
        isRealtimeEnabled: state.isRealtimeEnabled,
        memoryEnabled: state.memoryEnabled,
        sessions: state.sessions,
      }),
    }
  )
);
