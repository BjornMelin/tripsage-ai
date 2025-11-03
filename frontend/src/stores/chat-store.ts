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
  CONNECTING = "connecting",
  CONNECTED = "connected",
  DISCONNECTED = "disconnected",
  RECONNECTING = "reconnecting",
  ERROR = "error",
}

import type { RealtimeChannel } from "@supabase/supabase-js";
import { getBrowserClient } from "@/lib/supabase/client";
import type { ConversationMessage, MemoryContextResponse } from "@/types/memory";

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
 * WebSocket message event for real-time chat updates.
 *
 * Event structure for WebSocket messages containing chat content,
 * session identification, and metadata for real-time message streaming.
 */
export interface WebSocketMessageEvent {
  /** Event type identifier */
  type: "chat_message" | "chat_message_chunk";
  /** Session ID this event belongs to */
  sessionId: string;
  /** Message ID for chunked/streaming messages */
  messageId?: string;
  /** Text content of the message */
  content: string;
  /** Role of the message sender */
  role?: "user" | "assistant" | "system";
  /** Tool calls included in the message */
  toolCalls?: ToolCall[];
  /** File attachments in the message */
  attachments?: Attachment[];
  /** Whether this is the final chunk of a streaming message */
  isComplete?: boolean;
}

/**
 * WebSocket agent status update event.
 *
 * Event structure for real-time agent status updates including activity state,
 * current tasks, and progress information for UI synchronization.
 */
export interface WebSocketAgentStatusEvent {
  /** Event type identifier */
  type: "agent_status_update";
  /** Session ID this status update belongs to */
  sessionId: string;
  /** Whether the agent is currently active */
  isActive: boolean;
  /** Current task description */
  currentTask?: string;
  /** Progress percentage of current task */
  progress: number;
  /** Human-readable status message */
  statusMessage?: string;
}

/**
 * Internal chat store state interface.
 *
 * Defines the complete state structure for the chat store including sessions,
 * real-time connection status, memory integration, and all action handlers.
 * Used internally by Zustand for type-safe state management.
 */
interface ChatState {
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

  // Realtime integration state
  connectionStatus: ConnectionStatus;
  isRealtimeEnabled: boolean;
  realtimeChannel: RealtimeChannel | null;
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

  // Realtime actions (no direct WS usage)
  connectRealtime: (sessionId: string) => Promise<void>;
  disconnectRealtime: () => void;
  setRealtimeEnabled: (enabled: boolean) => void;
  handleRealtimeMessage: (event: WebSocketMessageEvent) => void;
  handleAgentStatusUpdate: (event: WebSocketAgentStatusEvent) => void;
  setUserTyping: (sessionId: string, userId: string, username?: string) => void;
  removeUserTyping: (sessionId: string, userId: string) => void;
  clearTypingUsers: (sessionId: string) => void;
  addPendingMessage: (message: Message) => void;
  removePendingMessage: (messageId: string) => void;
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
 * @returns {ChatState} The chat store state and actions
 *
 * @example
 * ```typescript
 * const {
 *   sessions,
 *   currentSession,
 *   sendMessage,
 *   createSession,
 *   connectRealtime
 * } = useChatStore();
 * ```
 */
export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
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

      addPendingMessage: (message) => {
        set((state) => ({
          pendingMessages: [...state.pendingMessages, message],
        }));
      },

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

      clearError: () => set({ error: null }),

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
      connectionStatus: ConnectionStatus.DISCONNECTED,

      // Realtime actions
      connectRealtime: async (sessionId) => {
        const supabase = getBrowserClient();
        const prev = get().realtimeChannel;
        if (prev) {
          prev.unsubscribe();
        }

        try {
          set({ connectionStatus: ConnectionStatus.CONNECTING });
          const channel = supabase
            .channel(`session:${sessionId}`, { config: { private: true } })
            .on("broadcast", { event: "chat:message" }, (payload) => {
              const data = payload.payload as
                | { content?: string; role?: string; id?: string }
                | undefined;
              get().handleRealtimeMessage({
                content: data?.content || "",
                messageId: data?.id,
                role: (data?.role as "user" | "assistant" | "system") || "assistant",
                sessionId,
                type: "chat_message",
              });
            })
            .on("broadcast", { event: "chat:message_chunk" }, (payload) => {
              const data = payload.payload as
                | { content?: string; id?: string; is_final?: boolean }
                | undefined;
              get().handleRealtimeMessage({
                content: data?.content || "",
                isComplete: Boolean(data?.is_final),
                messageId: data?.id,
                sessionId,
                type: "chat_message_chunk",
              });
            })
            .on("broadcast", { event: "chat:typing" }, (payload) => {
              const data = payload.payload as
                | { userId?: string; isTyping?: boolean; username?: string }
                | undefined;
              if (!data?.userId) return;
              if (data.isTyping) {
                get().setUserTyping(sessionId, data.userId, data.username);
              } else {
                get().removeUserTyping(sessionId, data.userId);
              }
            })
            .on("broadcast", { event: "agent_status_update" }, (payload) => {
              const p = payload.payload as
                | {
                    isActive?: boolean;
                    currentTask?: string;
                    progress?: number;
                    statusMessage?: string;
                  }
                | undefined;
              get().handleAgentStatusUpdate({
                currentTask: p?.currentTask,
                isActive: Boolean(p?.isActive),
                progress: Number(p?.progress ?? 0),
                sessionId,
                statusMessage: p?.statusMessage,
                type: "agent_status_update",
              });
            });

          channel.subscribe((state, err) => {
            if (state === "SUBSCRIBED") {
              set({ connectionStatus: ConnectionStatus.CONNECTED });
            }
            if (err) {
              set({
                connectionStatus: ConnectionStatus.ERROR,
                error: err.message ?? "Realtime subscription error",
              });
            }
          });

          set({ realtimeChannel: channel });
        } catch (error) {
          console.error("Failed to connect Realtime:", error);
          set({
            connectionStatus: ConnectionStatus.ERROR,
            error: error instanceof Error ? error.message : "Realtime connection error",
          });
        }
      },

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

      disconnectRealtime: () => {
        const { realtimeChannel } = get();
        if (realtimeChannel) {
          realtimeChannel.unsubscribe();
        }
        set({
          connectionStatus: ConnectionStatus.DISCONNECTED,
          pendingMessages: [],
          realtimeChannel: null,
          typingUsers: {},
        });
      },
      error: null,

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

      handleAgentStatusUpdate: (event) => {
        const { currentSessionId } = get();
        if (!currentSessionId || event.sessionId !== currentSessionId) return;

        get().updateAgentStatus(currentSessionId, {
          currentTask: event.currentTask,
          isActive: event.isActive,
          progress: event.progress,
          statusMessage: event.statusMessage,
        });
      },

      handleRealtimeMessage: (event) => {
        const { currentSessionId } = get();
        if (!currentSessionId || event.sessionId !== currentSessionId) return;

        if (event.type === "chat_message") {
          // Add complete message
          get().addMessage(currentSessionId, {
            attachments: event.attachments,
            content: event.content,
            role: event.role || "assistant",
            toolCalls: event.toolCalls,
          });
        } else if (event.type === "chat_message_chunk") {
          // Handle streaming message chunks
          const existingMessage = get()
            .sessions.find((s) => s.id === currentSessionId)
            ?.messages.find((m) => m.id === event.messageId);

          if (existingMessage && event.messageId) {
            // Update existing streaming message
            get().updateMessage(currentSessionId, event.messageId, {
              content: existingMessage.content + event.content,
              isStreaming: !event.isComplete,
            });
          } else {
            // Create new streaming message
            const messageId = get().addMessage(currentSessionId, {
              content: event.content,
              isStreaming: !event.isComplete,
              role: "assistant",
            });

            // Store the mapping for future chunks
            if (event.messageId && messageId !== event.messageId) {
              // Handle message ID mapping if needed
            }
          }
        }
      },

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

      // Realtime integration defaults
      realtimeChannel: null,

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

      renameSession: (sessionId, title) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? { ...session, title, updatedAt: new Date().toISOString() }
              : session
          ),
        }));
      },

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

      setAutoSyncMemory: (enabled) => {
        set({ autoSyncMemory: enabled });
      },

      setCurrentSession: (sessionId) => {
        set({ currentSessionId: sessionId });
      },

      setMemoryEnabled: (enabled) => {
        set({ memoryEnabled: enabled });
      },

      setRealtimeEnabled: (enabled) => {
        set({ isRealtimeEnabled: enabled });

        if (!enabled) {
          get().disconnectRealtime();
        }
      },

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
