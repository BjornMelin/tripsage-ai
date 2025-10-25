/**
 * @fileoverview React hook for AI chat functionality.
 *
 * Provides interface for sending messages, handling streaming responses,
 * managing tool calls, and maintaining chat session state.
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { z } from "zod";
import { useApiKeyStore } from "@/stores/api-key-store";
import { useChatStore } from "@/stores/chat-store";
import type {
  Attachment,
  ChatSession,
  Message,
  ToolCall,
  ToolResult,
} from "@/types/chat";

// Zod schemas for validation
// const SessionIdSchema = z.string().min(1, "Session ID cannot be empty").optional(); // Future validation

/** Schema for validating message content. */
const MessageContentSchema = z.string().min(1, "Message content cannot be empty");

/** Schema for validating attachment arrays. */
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

/**
 * Options for configuring the useChatAi hook.
 */
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

/**
 * React hook for managing AI chat functionality with streaming responses.
 *
 * This hook provides a complete interface for interacting with AI chat services,
 * including message sending, streaming response handling, tool call management,
 * and session state management. It includes authentication validation and
 * automatic session creation.
 *
 * @param options - Configuration options for the chat hook.
 * @param options.sessionId - Optional session ID. If not provided, generates a new one.
 * @param options.initialMessages - Initial messages to populate the chat session.
 * @param options.onNewSession - Callback invoked when a new session is created.
 * @returns Object containing chat state, actions, and authentication status.
 * @returns .sessionId - Current chat session ID.
 * @returns .messages - Array of messages in the current session.
 * @returns .isLoading - Whether a message is currently being sent.
 * @returns .error - Current error message if any.
 * @returns .isAuthenticated - Whether the user is authenticated.
 * @returns .isInitialized - Whether the hook has completed initialization.
 * @returns .isApiKeyValid - Whether a valid API key is configured.
 * @returns .authError - Authentication-related error message.
 * @returns .activeToolCalls - Currently executing tool calls.
 * @returns .toolResults - Results from completed tool calls.
 * @returns .sendMessage - Function to send a new message.
 * @returns .stopGeneration - Function to stop ongoing message generation.
 * @returns .reload - Placeholder for reload functionality.
 * @returns .retryToolCall - Function to retry a failed tool call.
 * @returns .cancelToolCall - Function to cancel an active tool call.
 */
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
      // Ensure subsequent operations target the created session
      sessionIdRef.current = createdSessionId;

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
    if (currentSessionId !== sessionIdRef.current) {
      setCurrentSession(sessionIdRef.current);
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
    setActiveToolCalls((prev) => {
      const next = new Map(prev);
      next.set(toolCall.id, toolCall);
      return next;
    });
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

  // Local loading/error state now that we call backend directly
  const [sendingStatus, setSendingStatus] = useState<
    "idle" | "submitting" | "streaming"
  >("idle");
  const [localError, setLocalError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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

        // Add the user message to our store
        addMessage(sessionIdRef.current, {
          role: "user",
          content: validatedContent,
          attachments: validatedAttachments,
        });

        // Send to backend FastAPI chat endpoint
        void (async () => {
          try {
            setSendingStatus("submitting");
            setLocalError(null);

            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
            const endpoint = `${apiUrl.replace(/\/$/, "")}/api/chat/stream`;

            // Build a minimal ChatRequest payload using recent session messages
            const session = sessions.find((s) => s.id === sessionIdRef.current);
            const recent = (session?.messages || []).slice(-20).map((m) => ({
              role: m.role,
              content: m.content,
            }));
            const body = JSON.stringify({ messages: recent });

            // Configure abort controller + timeout
            abortRef.current?.abort();
            abortRef.current = new AbortController();
            const signal = abortRef.current.signal;
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
            timeoutRef.current = setTimeout(() => {
              abortRef.current?.abort();
            }, 60_000);

            const response = await fetch(endpoint, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                Accept: "text/event-stream",
              },
              credentials: "include",
              body,
              signal,
            });

            if (!response.ok || !response.body) {
              const err = await response.json().catch(() => ({}));
              throw new Error(
                err?.detail || err?.error || `Chat failed (${response.status})`
              );
            }
            // Prepare streaming decode
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            // Create placeholder assistant message to progressively update
            const placeholderId = addMessage(sessionIdRef.current, {
              role: "assistant",
              content: "",
            });

            while (true) {
              const { value, done } = await reader.read();
              if (done) break;
              const chunk = decoder.decode(value, { stream: true });
              buffer += chunk;

              // Process complete SSE events separated by double newline
              let idx;
              while ((idx = buffer.indexOf("\n\n")) !== -1) {
                const raw = buffer.slice(0, idx).trim();
                buffer = buffer.slice(idx + 2);

                if (raw.startsWith("data:")) {
                  const dataStr = raw.slice(5).trim();
                  if (dataStr === "[DONE]") {
                    break;
                  }
                  try {
                    const evt = JSON.parse(dataStr) as {
                      type?: string;
                      content?: string;
                    };
                    if (evt.type === "delta" && evt.content) {
                      // Append token to placeholder content
                      const current =
                        sessions
                          .find((s) => s.id === sessionIdRef.current)
                          ?.messages.find((m) => m.id === placeholderId)?.content || "";
                      updateMessage(sessionIdRef.current, placeholderId, {
                        content: current + evt.content,
                      });
                    }
                  } catch {
                    // ignore malformed data
                  }
                }
              }
            }

            // Done
            setSendingStatus("idle");
            updateAgentStatus(sessionIdRef.current, {
              isActive: false,
              statusMessage: "",
            });
          } catch (e) {
            const msg = e instanceof Error ? e.message : "Chat request failed";
            setLocalError(msg);
            updateAgentStatus(sessionIdRef.current, {
              isActive: false,
              statusMessage: msg,
            });
            setSendingStatus("idle");
          } finally {
            if (timeoutRef.current) {
              clearTimeout(timeoutRef.current);
              timeoutRef.current = null;
            }
            // Clear tool-call tracking between messages
            setActiveToolCalls(new Map());
            setToolResults(new Map());
          }
        })();
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
      sessions,
      addMessage,
      updateAgentStatus,
      isInitialized,
      isAuthenticated,
      isApiKeyValid,
    ]
  );

  // Handle stopping the generation
  const stopGeneration = useCallback(() => {
    // Abort in-flight request and clear status/UI
    abortRef.current?.abort();
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    stopStreaming();
    updateAgentStatus(sessionIdRef.current, { isActive: false, statusMessage: "" });
  }, [stopStreaming, updateAgentStatus]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  return {
    // Chat state
    sessionId: sessionIdRef.current,
    messages: sessions.find((s) => s.id === sessionIdRef.current)?.messages || [],
    isLoading: sendingStatus !== "idle",
    error: localError || authError || storeAuthError,

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
    reload: () => undefined,

    // Tool call actions
    retryToolCall,
    cancelToolCall,
  };
}
