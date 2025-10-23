"use client";

import { useChat } from "@ai-sdk/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { z } from "zod";
import { useApiKeyStore } from "@/stores/api-key-store";
import { useChatStore } from "@/stores/chat-store";
import type {
  Attachment,
  ChatSession,
  Message,
  MessageRole,
  ToolCall,
  ToolResult,
} from "@/types/chat";

// Zod schemas for validation
// const SessionIdSchema = z.string().min(1, "Session ID cannot be empty").optional(); // Future validation

const MessageContentSchema = z.string().min(1, "Message content cannot be empty");

const AttachmentArraySchema = z
  .array(
    z.object({
      id: z.string(),
      url: z.string().url(),
      name: z.string().optional(),
      contentType: z.string().optional(),
      size: z.number().positive().optional(),
    })
  )
  .default([]);

interface UseChatAiOptions {
  /**
   * The ID of the chat session. If not provided, a new one will be created.
   */
  sessionId?: string;

  /**
   * Initial messages to start the chat with.
   */
  initialMessages?: Message[];

  /**
   * Callback when a new session is created.
   */
  onNewSession?: (session: ChatSession) => void;
}

export function useChatAi(options: UseChatAiOptions = {}) {
  const { sessionId: providedSessionId, initialMessages = [], onNewSession } = options;

  // Generate a session ID if not provided
  const sessionIdRef = useRef<string>(providedSessionId || uuidv4());

  // Auth and API key state
  const [authError, setAuthError] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // Tool call state
  const [activeToolCalls, setActiveToolCalls] = useState<Map<string, ToolCall>>(
    new Map()
  );
  const [toolResults, setToolResults] = useState<Map<string, ToolResult>>(new Map());

  const {
    isAuthenticated,
    isApiKeyValid,
    authError: storeAuthError,
    token,
    loadKeys,
    validateKey,
    setAuthError: setStoreAuthError,
  } = useApiKeyStore();

  // Access chat store functions
  const {
    sessions,
    currentSessionId,
    setCurrentSession,
    createSession,
    addMessage,
    updateMessage,
    updateAgentStatus,
    stopStreaming,
  } = useChatStore();

  // Initialize authentication and validate API keys
  useEffect(() => {
    const initializeAuth = async () => {
      if (!isAuthenticated) {
        setAuthError("Authentication required. Please log in to use the chat.");
        setIsInitialized(false);
        return;
      }

      // Load keys if authenticated
      try {
        await loadKeys();

        // Validate the OpenAI key (required for chat)
        const hasValidKey = await validateKey("openai");
        if (!hasValidKey) {
          setAuthError(
            "Valid OpenAI API key required. Please add one in your API settings."
          );
          setIsInitialized(false);
          return;
        }

        setAuthError(null);
        setStoreAuthError(null);
        setIsInitialized(true);
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Authentication failed";
        setAuthError(message);
        setIsInitialized(false);
      }
    };

    initializeAuth();
  }, [isAuthenticated, loadKeys, validateKey, setStoreAuthError]);

  // Ensure the session exists (only after auth is initialized)
  useEffect(() => {
    if (!isInitialized) return;

    const sessionId = sessionIdRef.current;

    // Check if this session already exists
    const existingSession = sessions.find((s) => s.id === sessionId);

    if (!existingSession) {
      // Create a new session using the store method
      const createdSessionId = createSession("New Chat");

      // Note: The onNewSession callback will be called when the session is available
      // since sessions is a derived state that might not be immediately updated
      if (onNewSession) {
        // Create a temporary session object for the callback
        const tempSession: ChatSession = {
          id: createdSessionId,
          title: "New Chat",
          messages: initialMessages,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        onNewSession(tempSession);
      }
    }

    // Set as active session
    if (currentSessionId !== sessionId) {
      setCurrentSession(sessionId);
    }
  }, [
    isInitialized,
    sessions,
    currentSessionId,
    setCurrentSession,
    createSession,
    initialMessages,
    onNewSession,
  ]);

  // Tool call management functions
  const addToolCall = useCallback((toolCall: ToolCall) => {
    setActiveToolCalls((prev) => new Map(prev.set(toolCall.id, toolCall)));
  }, []);

  const updateToolCall = useCallback(
    (toolCallId: string, updates: Partial<ToolCall>) => {
      setActiveToolCalls((prev) => {
        const newMap = new Map(prev);
        const existing = newMap.get(toolCallId);
        if (existing) {
          newMap.set(toolCallId, { ...existing, ...updates });
        }
        return newMap;
      });
    },
    []
  );

  const addToolResult = useCallback(
    (result: ToolResult) => {
      setToolResults((prev) => new Map(prev.set(result.callId, result)));
      // Update the tool call status
      updateToolCall(result.callId, {
        status: result.status === "success" ? "completed" : "error",
        result: result.result,
        error: result.errorMessage,
        executionTime: result.executionTime,
      });
    },
    [updateToolCall]
  );

  const retryToolCall = useCallback(
    async (toolCallId: string) => {
      const toolCall = activeToolCalls.get(toolCallId);
      if (!toolCall) return;

      // Reset tool call status
      updateToolCall(toolCallId, { status: "pending", error: undefined });

      // Remove any existing result
      setToolResults((prev) => {
        const newMap = new Map(prev);
        newMap.delete(toolCallId);
        return newMap;
      });

      // TODO: Implement actual retry logic with API call
      console.log("Retrying tool call:", toolCallId);
    },
    [activeToolCalls, updateToolCall]
  );

  const cancelToolCall = useCallback(
    (toolCallId: string) => {
      updateToolCall(toolCallId, { status: "cancelled" });

      // TODO: Implement actual cancellation with API call
      console.log("Cancelling tool call:", toolCallId);
    },
    [updateToolCall]
  );

  // Handle streaming tool call chunks
  const _handleToolCallChunk = useCallback(
    (chunk: string) => {
      try {
        if (chunk.startsWith("9:")) {
          // Tool call chunk
          const toolCallData = JSON.parse(chunk.slice(2));
          const toolCall: ToolCall = {
            id: toolCallData.id,
            name: toolCallData.name,
            arguments: toolCallData.args,
            status: "executing",
            sessionId: sessionIdRef.current,
          };
          addToolCall(toolCall);
        } else if (chunk.startsWith("a:")) {
          // Tool result chunk
          const resultData = JSON.parse(chunk.slice(2));
          const toolResult: ToolResult = {
            callId: resultData.callId,
            result: resultData.result,
            status: resultData.result?.status === "error" ? "error" : "success",
            errorMessage: resultData.result?.error,
            executionTime: resultData.result?.executionTime,
          };
          addToolResult(toolResult);
        }
      } catch (error) {
        console.warn("Failed to parse tool call chunk:", chunk, error);
      }
    },
    [addToolCall, addToolResult]
  );

  // Set up Vercel AI SDK chat (only if initialized)
  const {
    messages: aiSdkMessages,
    sendMessage: sendChatMessage,
    status,
    error,
    stop,
    regenerate,
  } = useChat({
    id: sessionIdRef.current,
    onFinish: ({ message }) => {
      // Update message with tool call information
      if (activeToolCalls.size > 0) {
        const toolCallsArray = Array.from(activeToolCalls.values()).map((toolCall) => ({
          id: toolCall.id,
          name: toolCall.name,
          arguments: toolCall.arguments || {},
          state: "call" as const,
        }));
        const toolResultsArray = Array.from(toolResults.values()).map((toolResult) => ({
          callId: toolResult.callId,
          result: toolResult.result || null, // Ensure result is present
        }));

        updateMessage(sessionIdRef.current, message.id, {
          toolCalls: toolCallsArray,
          toolResults: toolResultsArray,
        });
      }

      // Set agent to idle when message is complete
      updateAgentStatus(sessionIdRef.current, {
        isActive: false,
        statusMessage: "",
      });

      // Clear active tool calls for next message
      setActiveToolCalls(new Map());
      setToolResults(new Map());
    },
    onError: (error) => {
      console.error("Chat error:", error);

      // Parse error for specific handling
      let errorMessage = "An error occurred while processing your request";
      // let errorStatus = "error"; // Future use

      if (error.message) {
        // Check for specific error patterns
        if (error.message.includes("timeout") || error.message.includes("TIMEOUT")) {
          errorMessage = "Request timed out. Please try again.";
          // errorStatus = "timeout"; // Future use
        } else if (
          error.message.includes("Authentication required") ||
          error.message.includes("AUTH_REQUIRED")
        ) {
          errorMessage = "Authentication required. Please check your API keys.";
          // errorStatus = "auth_error"; // Future use
        } else if (
          error.message.includes("Rate limited") ||
          error.message.includes("RATE_LIMITED")
        ) {
          errorMessage = "Too many requests. Please wait a moment and try again.";
          // errorStatus = "rate_limited"; // Future use
        } else if (
          error.message.includes("Service unavailable") ||
          error.message.includes("SERVICE_UNAVAILABLE")
        ) {
          errorMessage =
            "AI service is temporarily unavailable. Please try again later.";
          // errorStatus = "service_unavailable"; // Future use
        } else if (error.message.includes("Model not available")) {
          errorMessage =
            "The selected AI model is not available. Please try a different model.";
          // errorStatus = "model_unavailable"; // Future use
        } else {
          errorMessage = error.message;
        }
      }

      updateAgentStatus(sessionIdRef.current, {
        isActive: false,
        statusMessage: errorMessage,
      });
    },
  });

  const partsToText = (parts?: { type: string; text?: string }[]) =>
    (parts || [])
      .filter((p) => p?.type === "text" && typeof p.text === "string")
      .map((p) => p.text as string)
      .join("");

  // Sync AI SDK messages to our store
  useEffect(() => {
    const lastMessage = aiSdkMessages[aiSdkMessages.length - 1];

    if (!lastMessage) return;

    const sessionMessages =
      sessions.find((s) => s.id === sessionIdRef.current)?.messages || [];
    const existingMessage = sessionMessages.find((m) => m.id === lastMessage.id);

    const content =
      partsToText((lastMessage as any).parts) || (lastMessage as any).content || "";
    const role = lastMessage.role as MessageRole;
    if (existingMessage) {
      if (existingMessage.content !== content) {
        updateMessage(sessionIdRef.current, lastMessage.id, { content });
      }
    } else {
      addMessage(sessionIdRef.current, { role, content });
    }
  }, [aiSdkMessages, sessions, addMessage, updateMessage]);

  // Handle sending a user message
  const sendMessage = useCallback(
    (content: string, attachments: Attachment[] = []) => {
      // Validate inputs with Zod
      try {
        const validatedContent = MessageContentSchema.parse(content);
        const validatedAttachments = AttachmentArraySchema.parse(attachments);

        // Check if initialized and authenticated
        if (!isInitialized || !isAuthenticated) {
          setAuthError("Please authenticate before sending messages");
          return;
        }

        // Check for valid API key
        if (!isApiKeyValid) {
          setAuthError("Valid API key required before sending messages");
          return;
        }

        // Set agent status to thinking
        updateAgentStatus(sessionIdRef.current, {
          isActive: true,
          statusMessage: "Thinking...",
        });

        // Create a unique ID for this message
        uuidv4(); // Generated for future message tracking

        // Add the user message to our store
        addMessage(sessionIdRef.current, {
          role: "user",
          content: validatedContent,
          attachments: validatedAttachments,
        });

        // Send via AI SDK v5
        void sendChatMessage({ text: validatedContent });
      } catch (error) {
        // Handle Zod validation errors
        if (error instanceof z.ZodError) {
          const errorMessage = error.issues.map((e) => e.message).join(", ");
          setAuthError(`Invalid input: ${errorMessage}`);
        } else {
          setAuthError("An error occurred while processing your message");
        }
        return;
      }
    },
    [
      addMessage,
      sendChatMessage,
      updateAgentStatus,
      isInitialized,
      isAuthenticated,
      isApiKeyValid,
    ]
  );

  // Handle stopping the generation
  const stopGeneration = useCallback(() => {
    stop();
    stopStreaming();
    updateAgentStatus(sessionIdRef.current, {
      isActive: false,
      statusMessage: "",
    });
  }, [stop, stopStreaming, updateAgentStatus]);

  return {
    // Chat state
    sessionId: sessionIdRef.current,
    messages: sessions.find((s) => s.id === sessionIdRef.current)?.messages || [],
    isLoading: status === "submitted" || status === "streaming",
    error: error || authError || storeAuthError,

    // Auth state
    isAuthenticated,
    isInitialized,
    isApiKeyValid,
    authError: authError || storeAuthError,

    // Tool call state
    activeToolCalls: Array.from(activeToolCalls.values()),
    toolResults: Array.from(toolResults.values()),

    // Actions
    sendMessage,
    stopGeneration,
    reload: regenerate,

    // Tool call actions
    retryToolCall,
    cancelToolCall,
  };
}
