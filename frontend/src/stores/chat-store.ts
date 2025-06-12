import {
  ConnectionStatus,
  type WebSocketClient,
  WebSocketEventType,
} from "@/lib/websocket/websocket-client";
import type {
  ConversationMessage,
  Memory,
  MemoryContextResponse,
  UserPreferences,
} from "@/types/memory";
import { z } from "zod";
import { create } from "zustand";
import { persist } from "zustand/middleware";

// Enhanced Message type with support for tool calls and attachments
export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;

  // Additional fields for advanced features
  toolCalls?: ToolCall[];
  toolResults?: ToolResult[];
  attachments?: Attachment[];
  isStreaming?: boolean;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  state: "call" | "partial-call" | "result";
}

export interface ToolResult {
  callId: string;
  result: unknown;
}

export interface Attachment {
  id: string;
  url: string;
  name?: string;
  contentType?: string;
  size?: number;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
  agentStatus?: AgentStatus;

  // Memory integration
  memoryContext?: MemoryContextResponse;
  userId?: string;
  lastMemorySync?: string;
}

export interface AgentStatus {
  isActive: boolean;
  currentTask?: string;
  progress: number;
  statusMessage?: string;
}

// Request options for sending messages
export interface SendMessageOptions {
  attachments?: File[];
  systemPrompt?: string;
  temperature?: number;
  tools?: Record<string, unknown>[];
}

// WebSocket event types
export interface WebSocketMessageEvent {
  type: "chat_message" | "chat_message_chunk";
  sessionId: string;
  messageId?: string;
  content: string;
  role?: "user" | "assistant" | "system";
  toolCalls?: ToolCall[];
  attachments?: Attachment[];
  isComplete?: boolean;
}

export interface WebSocketAgentStatusEvent {
  type: "agent_status_update";
  sessionId: string;
  isActive: boolean;
  currentTask?: string;
  progress: number;
  statusMessage?: string;
}

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

  // WebSocket integration
  websocketClient: WebSocketClient | null;
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

  // WebSocket actions
  connectWebSocket: (sessionId: string, token: string) => Promise<void>;
  disconnectWebSocket: () => void;
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
const sessionDataSchema = z.object({
  id: z.string(),
  title: z.string(),
  messages: z.array(
    z.object({
      id: z.string(),
      role: z.enum(["user", "assistant", "system"]),
      content: z.string(),
      timestamp: z.string(),
      toolCalls: z
        .array(
          z.object({
            id: z.string(),
            name: z.string(),
            arguments: z.record(z.unknown()),
            state: z.enum(["call", "partial-call", "result"]),
          })
        )
        .optional(),
      attachments: z
        .array(
          z.object({
            id: z.string(),
            url: z.string(),
            name: z.string().optional(),
            contentType: z.string().optional(),
          })
        )
        .optional(),
    })
  ),
  createdAt: z.string(),
  updatedAt: z.string(),
});

// Abort controller for canceling stream requests
let abortController: AbortController | null = null;

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      sessions: [],
      currentSessionId: null,
      isLoading: false,
      isStreaming: false,
      error: null,

      // Memory integration defaults
      memoryEnabled: true,
      autoSyncMemory: true,

      // WebSocket integration defaults
      websocketClient: null,
      connectionStatus: ConnectionStatus.DISCONNECTED,
      isRealtimeEnabled: true,
      typingUsers: {},
      pendingMessages: [],

      get currentSession() {
        const { sessions, currentSessionId } = get();
        if (!currentSessionId) return null;
        return sessions.find((session) => session.id === currentSessionId) || null;
      },

      createSession: (title, userId) => {
        const timestamp = new Date().toISOString();
        const sessionId = Date.now().toString();

        const newSession: ChatSession = {
          id: sessionId,
          title: title || "New Conversation",
          messages: [],
          createdAt: timestamp,
          updatedAt: timestamp,
          agentStatus: {
            isActive: false,
            progress: 0,
          },
          userId: userId,
          memoryContext: undefined,
          lastMemorySync: undefined,
        };

        set((state) => ({
          sessions: [newSession, ...state.sessions],
          currentSessionId: sessionId,
        }));

        return sessionId;
      },

      setCurrentSession: (sessionId) => {
        set({ currentSessionId: sessionId });
      },

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

          return { sessions, currentSessionId };
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

      sendMessage: async (content, options = {}) => {
        const {
          currentSessionId,
          currentSession,
          websocketClient,
          isRealtimeEnabled,
          connectionStatus,
        } = get();

        // Create a new session if none exists
        let sessionId = currentSessionId;
        if (!sessionId || !currentSession) {
          sessionId = get().createSession("New Conversation");
        }

        // Add user message
        const userMessageId = get().addMessage(sessionId, {
          role: "user",
          content,
          attachments: options.attachments?.map((file) => ({
            id: Date.now().toString(),
            url: URL.createObjectURL(file),
            name: file.name,
            contentType: file.type,
            size: file.size,
          })),
        });

        set({ isLoading: true, error: null });

        // Use WebSocket if available and connected
        if (
          isRealtimeEnabled &&
          websocketClient &&
          connectionStatus === ConnectionStatus.CONNECTED
        ) {
          try {
            await websocketClient.send("chat_message", {
              content,
              sessionId,
              attachments: options.attachments?.map((file) => ({
                name: file.name,
                contentType: file.type,
                size: file.size,
              })),
              systemPrompt: options.systemPrompt,
              temperature: options.temperature,
              tools: options.tools,
            });

            // WebSocket will handle the response via event handlers
            set({ isLoading: false });
            return;
          } catch (error) {
            console.warn("WebSocket send failed, falling back to HTTP:", error);
            // Fall through to HTTP implementation
          }
        }

        try {
          // Update agent status to show it's processing
          get().updateAgentStatus(sessionId, {
            isActive: true,
            currentTask: "Processing your request",
            progress: 30,
            statusMessage: "Analyzing your query...",
          });

          // This will be replaced with actual API call
          await new Promise((resolve) => setTimeout(resolve, 1000));

          // Mock AI response
          get().addMessage(sessionId, {
            role: "assistant",
            content: `I've received your message: "${content}". This is a placeholder response from the AI assistant that will be replaced with the actual API integration.`,
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
            role: "system",
            content:
              "Sorry, there was an error processing your request. Please try again.",
          });
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
          role: "user",
          content,
          attachments: options.attachments?.map((file) => ({
            id: Date.now().toString(),
            url: URL.createObjectURL(file),
            name: file.name,
            contentType: file.type,
            size: file.size,
          })),
        });

        // Create a placeholder message for streaming
        const assistantMessageId = get().addMessage(sessionId, {
          role: "assistant",
          content: "",
          isStreaming: true,
        });

        // Set streaming state and create abort controller
        set({ isStreaming: true, error: null });
        abortController = new AbortController();

        // Update agent status
        get().updateAgentStatus(sessionId, {
          isActive: true,
          currentTask: "Generating response",
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

      clearError: () => set({ error: null }),

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
              id: att.id,
              url: att.url.startsWith("blob:") ? "" : att.url, // Don't export blob URLs
              name: att.name,
              contentType: att.contentType,
            })),
          })),
        };

        return JSON.stringify(exportData, null, 2);
      },

      importSessionData: (jsonData) => {
        try {
          const data = JSON.parse(jsonData);

          // Validate the data structure
          const result = sessionDataSchema.safeParse(data);
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
            title: `${data.title} (Imported)`,
            updatedAt: timestamp,
            messages: data.messages,
          };

          set((state) => ({
            sessions: [importedSession, ...state.sessions],
            currentSessionId: sessionId,
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

      // Memory actions
      updateSessionMemoryContext: (sessionId, memoryContext) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  memoryContext,
                  lastMemorySync: new Date().toISOString(),
                  updatedAt: new Date().toISOString(),
                }
              : session
          ),
        }));
      },

      syncMemoryToSession: async (sessionId) => {
        const session = get().sessions.find((s) => s.id === sessionId);
        if (!session?.userId || !get().memoryEnabled) return;

        try {
          // Import memory hooks here to avoid circular dependencies
          const { useMemoryContext } = await import("@/hooks/use-memory");

          // Note: This would typically be handled by the component using the hook
          // This is a placeholder for the actual implementation
          console.log("Memory sync would fetch context for user:", session.userId);
        } catch (error) {
          console.error("Failed to sync memory to session:", error);
          set({ error: "Failed to sync memory context" });
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
              role: msg.role,
              content: msg.content,
              timestamp: msg.timestamp,
              metadata: {
                toolCalls: msg.toolCalls,
                toolResults: msg.toolResults,
                attachments: msg.attachments,
              },
            })
          );

          // Import memory hooks here to avoid circular dependencies
          const { useAddConversationMemory } = await import("@/hooks/use-memory");

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

      setMemoryEnabled: (enabled) => {
        set({ memoryEnabled: enabled });
      },

      setAutoSyncMemory: (enabled) => {
        set({ autoSyncMemory: enabled });
      },

      // WebSocket actions
      connectWebSocket: async (sessionId, token) => {
        const { websocketClient } = get();

        // Disconnect existing connection if any
        if (websocketClient) {
          websocketClient.disconnect();
        }

        try {
          // Import WebSocketClient dynamically to avoid SSR issues
          const { WebSocketClient } = await import("@/lib/websocket/websocket-client");

          // Construct proper WebSocket URL with /api prefix
          const wsBaseUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api";
          const newClient = new WebSocketClient({
            url: `${wsBaseUrl}/ws/chat/${sessionId}`,
            token,
            sessionId,
            channels: [`session:${sessionId}`],
            reconnectAttempts: 5,
            reconnectDelay: 1000,
            heartbeatInterval: 30000,
            debug: process.env.NODE_ENV === "development",
          });

          // Set up event handlers
          newClient.on("connect", () => {
            set({ connectionStatus: ConnectionStatus.CONNECTED });
            console.log("WebSocket connected successfully");
          });

          newClient.on("disconnect", () => {
            set({ connectionStatus: ConnectionStatus.DISCONNECTED });
          });

          newClient.on("error", (error) => {
            console.error("WebSocket error:", error);
            set({
              connectionStatus: ConnectionStatus.ERROR,
              error:
                error instanceof Error ? error.message : "WebSocket connection error",
            });
          });

          newClient.on(
            "reconnect",
            (data: { attempt: number; maxAttempts: number }) => {
              set({ connectionStatus: ConnectionStatus.RECONNECTING });
              console.log(
                `WebSocket reconnecting... Attempt ${data.attempt}/${data.maxAttempts}`
              );
            }
          );

          // Handle incoming messages
          newClient.on(WebSocketEventType.CHAT_MESSAGE, (event: any) => {
            get().handleRealtimeMessage({
              type: "chat_message",
              sessionId,
              content: event.payload.message?.content || "",
              role: event.payload.message?.role,
              messageId: event.payload.message?.id,
            });
          });

          newClient.on(WebSocketEventType.CHAT_MESSAGE_CHUNK, (event: any) => {
            get().handleRealtimeMessage({
              type: "chat_message_chunk",
              sessionId,
              content: event.payload.content || "",
              messageId: event.id,
              isComplete: event.payload.is_final || false,
            });
          });

          newClient.on(WebSocketEventType.AGENT_STATUS_UPDATE, (event: any) => {
            get().handleAgentStatusUpdate({
              type: "agent_status_update",
              sessionId,
              isActive: event.payload.is_active || false,
              currentTask: event.payload.current_task,
              progress: event.payload.progress || 0,
              statusMessage: event.payload.status_message,
            });
          });

          newClient.on(WebSocketEventType.CHAT_TYPING_START, () => {
            // Handle typing indicator start
            set({ isStreaming: true });
          });

          newClient.on(WebSocketEventType.CHAT_TYPING_STOP, () => {
            // Handle typing indicator stop
            set({ isStreaming: false });
          });

          // Store client and connect
          set({
            websocketClient: newClient,
            connectionStatus: ConnectionStatus.CONNECTING,
          });
          await newClient.connect();
        } catch (error) {
          console.error("Failed to connect WebSocket:", error);
          set({
            connectionStatus: ConnectionStatus.ERROR,
            error:
              error instanceof Error ? error.message : "Failed to connect WebSocket",
          });
        }
      },

      disconnectWebSocket: () => {
        const { websocketClient } = get();
        if (websocketClient) {
          websocketClient.disconnect();
        }
        // Always update state to disconnected, regardless of client existence
        set({
          websocketClient: null,
          connectionStatus: ConnectionStatus.DISCONNECTED,
          typingUsers: {},
          pendingMessages: [],
        });
      },

      setRealtimeEnabled: (enabled) => {
        set({ isRealtimeEnabled: enabled });

        if (!enabled) {
          get().disconnectWebSocket();
        }
      },

      handleRealtimeMessage: (event) => {
        const { currentSessionId } = get();
        if (!currentSessionId || event.sessionId !== currentSessionId) return;

        if (event.type === "chat_message") {
          // Add complete message
          get().addMessage(currentSessionId, {
            role: event.role || "assistant",
            content: event.content,
            toolCalls: event.toolCalls,
            attachments: event.attachments,
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
              role: "assistant",
              content: event.content,
              isStreaming: !event.isComplete,
            });

            // Store the mapping for future chunks
            if (event.messageId && messageId !== event.messageId) {
              // Handle message ID mapping if needed
            }
          }
        }
      },

      handleAgentStatusUpdate: (event) => {
        const { currentSessionId } = get();
        if (!currentSessionId || event.sessionId !== currentSessionId) return;

        get().updateAgentStatus(currentSessionId, {
          isActive: event.isActive,
          currentTask: event.currentTask,
          progress: event.progress,
          statusMessage: event.statusMessage,
        });
      },

      setUserTyping: (sessionId, userId, username) => {
        set((state) => ({
          typingUsers: {
            ...state.typingUsers,
            [`${sessionId}_${userId}`]: {
              userId,
              username,
              timestamp: new Date().toISOString(),
            },
          },
        }));

        // Auto-remove typing indicator after 3 seconds
        setTimeout(() => {
          get().removeUserTyping(sessionId, userId);
        }, 3000);
      },

      removeUserTyping: (sessionId, userId) => {
        set((state) => {
          const newTypingUsers = { ...state.typingUsers };
          delete newTypingUsers[`${sessionId}_${userId}`];
          return { typingUsers: newTypingUsers };
        });
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

      addPendingMessage: (message) => {
        set((state) => ({
          pendingMessages: [...state.pendingMessages, message],
        }));
      },

      removePendingMessage: (messageId) => {
        set((state) => ({
          pendingMessages: state.pendingMessages.filter((m) => m.id !== messageId),
        }));
      },
    }),
    {
      name: "chat-storage",
      partialize: (state) => ({
        sessions: state.sessions,
        currentSessionId: state.currentSessionId,
        memoryEnabled: state.memoryEnabled,
        autoSyncMemory: state.autoSyncMemory,
        isRealtimeEnabled: state.isRealtimeEnabled,
      }),
    }
  )
);
