import { useChat, type Message as AiMessage } from "ai/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { useChatStore } from "@/stores/chat-store";
import { useApiKeyStore } from "@/stores/api-key-store";
import type { Message, MessageRole, ChatSession, ToolCall, ToolResult } from "@/types/chat";

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
  const {
    sessionId: providedSessionId,
    initialMessages = [],
    onNewSession,
  } = options;

  // Generate a session ID if not provided
  const sessionIdRef = useRef<string>(providedSessionId || uuidv4());
  
  // Auth and API key state
  const [authError, setAuthError] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  
  // Tool call state
  const [activeToolCalls, setActiveToolCalls] = useState<Map<string, ToolCall>>(new Map());
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
    activeSessionId,
    setActiveSessionId,
    createSession,
    addMessage,
    updateMessage,
    setAgentStatus,
    cancelStream,
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
          setAuthError("Valid OpenAI API key required. Please add one in your API settings.");
          setIsInitialized(false);
          return;
        }

        setAuthError(null);
        setStoreAuthError(null);
        setIsInitialized(true);
      } catch (error) {
        const message = error instanceof Error ? error.message : "Authentication failed";
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
      // Create a new session
      const newSession: ChatSession = {
        id: sessionId,
        title: "New Chat",
        createdAt: new Date(),
        updatedAt: new Date(),
        messages: initialMessages,
      };

      createSession(newSession);

      if (onNewSession) {
        onNewSession(newSession);
      }
    }

    // Set as active session
    if (activeSessionId !== sessionId) {
      setActiveSessionId(sessionId);
    }
  }, [
    isInitialized,
    sessions,
    activeSessionId,
    setActiveSessionId,
    createSession,
    initialMessages,
    onNewSession,
  ]);

  // Tool call management functions
  const addToolCall = useCallback((toolCall: ToolCall) => {
    setActiveToolCalls(prev => new Map(prev.set(toolCall.id, toolCall)));
  }, []);

  const updateToolCall = useCallback((toolCallId: string, updates: Partial<ToolCall>) => {
    setActiveToolCalls(prev => {
      const newMap = new Map(prev);
      const existing = newMap.get(toolCallId);
      if (existing) {
        newMap.set(toolCallId, { ...existing, ...updates });
      }
      return newMap;
    });
  }, []);

  const addToolResult = useCallback((result: ToolResult) => {
    setToolResults(prev => new Map(prev.set(result.callId, result)));
    // Update the tool call status
    updateToolCall(result.callId, { 
      status: result.status === "success" ? "completed" : "error",
      result: result.result,
      error: result.errorMessage,
      executionTime: result.executionTime
    });
  }, [updateToolCall]);

  const retryToolCall = useCallback(async (toolCallId: string) => {
    const toolCall = activeToolCalls.get(toolCallId);
    if (!toolCall) return;

    // Reset tool call status
    updateToolCall(toolCallId, { status: "pending", error: undefined });
    
    // Remove any existing result
    setToolResults(prev => {
      const newMap = new Map(prev);
      newMap.delete(toolCallId);
      return newMap;
    });

    // TODO: Implement actual retry logic with API call
    console.log("Retrying tool call:", toolCallId);
  }, [activeToolCalls, updateToolCall]);

  const cancelToolCall = useCallback((toolCallId: string) => {
    updateToolCall(toolCallId, { status: "cancelled" });
    
    // TODO: Implement actual cancellation with API call
    console.log("Cancelling tool call:", toolCallId);
  }, [updateToolCall]);

  // Handle streaming tool call chunks
  const handleToolCallChunk = useCallback((chunk: string) => {
    try {
      if (chunk.startsWith('9:')) {
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
      } else if (chunk.startsWith('a:')) {
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
  }, [addToolCall, addToolResult]);

  // Convert our messages to AI SDK format
  const aiMessages: AiMessage[] =
    sessions
      .find((s) => s.id === sessionIdRef.current)
      ?.messages.map((msg) => ({
        id: msg.id,
        role: msg.role.toLowerCase() as "user" | "assistant" | "system",
        content: msg.content,
      })) || [];

  // Set up Vercel AI SDK chat (only if initialized)
  const {
    messages: aiSdkMessages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    error,
    stop,
    reload,
  } = useChat({
    api: "/api/chat",
    initialMessages: aiMessages,
    id: sessionIdRef.current,
    headers: {
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    onResponse: (response) => {
      // Check for rate limit headers
      const retryAfter = response.headers.get("X-RateLimit-Reset");
      if (response.status === 429 && retryAfter) {
        const resetTime = new Date(Number.parseInt(retryAfter) * 1000);
        setAgentStatus({
          sessionId: sessionIdRef.current,
          status: "error",
          message: `Rate limited. Try again after ${resetTime.toLocaleTimeString()}`,
        });
        return;
      }

      // Set agent to processing when we get a response
      setAgentStatus({
        sessionId: sessionIdRef.current,
        status: "processing",
        message: "Processing your request...",
      });

      // Handle streaming tool calls
      if (response.body) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        const processChunk = async () => {
          try {
            const { done, value } = await reader.read();
            if (done) return;
            
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');
            
            for (const line of lines) {
              if (line.trim()) {
                handleToolCallChunk(line.trim());
              }
            }
            
            // Continue processing
            processChunk();
          } catch (error) {
            console.warn("Error processing stream chunk:", error);
          }
        };
        
        processChunk();
      }
    },
    onFinish: (message) => {
      // Update message with tool call information
      if (activeToolCalls.size > 0) {
        const toolCallsArray = Array.from(activeToolCalls.values());
        const toolResultsArray = Array.from(toolResults.values());
        
        updateMessage({
          sessionId: sessionIdRef.current,
          messageId: message.id,
          updates: {
            toolCalls: toolCallsArray,
            toolResults: toolResultsArray,
          },
        });
      }

      // Set agent to idle when message is complete
      setAgentStatus({
        sessionId: sessionIdRef.current,
        status: "idle",
        message: "",
      });

      // Clear active tool calls for next message
      setActiveToolCalls(new Map());
      setToolResults(new Map());
    },
    onError: (error) => {
      console.error("Chat error:", error);

      // Parse error for specific handling
      let errorMessage = "An error occurred while processing your request";
      let errorStatus = "error";

      if (error.message) {
        // Check for specific error patterns
        if (
          error.message.includes("timeout") ||
          error.message.includes("TIMEOUT")
        ) {
          errorMessage = "Request timed out. Please try again.";
          errorStatus = "timeout";
        } else if (
          error.message.includes("Authentication required") ||
          error.message.includes("AUTH_REQUIRED")
        ) {
          errorMessage = "Authentication required. Please check your API keys.";
          errorStatus = "auth_error";
        } else if (
          error.message.includes("Rate limited") ||
          error.message.includes("RATE_LIMITED")
        ) {
          errorMessage =
            "Too many requests. Please wait a moment and try again.";
          errorStatus = "rate_limited";
        } else if (
          error.message.includes("Service unavailable") ||
          error.message.includes("SERVICE_UNAVAILABLE")
        ) {
          errorMessage =
            "AI service is temporarily unavailable. Please try again later.";
          errorStatus = "service_unavailable";
        } else if (error.message.includes("Model not available")) {
          errorMessage =
            "The selected AI model is not available. Please try a different model.";
          errorStatus = "model_unavailable";
        } else {
          errorMessage = error.message;
        }
      }

      setAgentStatus({
        sessionId: sessionIdRef.current,
        status: errorStatus as any,
        message: errorMessage,
      });
    },
  });

  // Sync AI SDK messages to our store
  useEffect(() => {
    const lastMessage = aiSdkMessages[aiSdkMessages.length - 1];

    if (!lastMessage) return;

    const sessionMessages =
      sessions.find((s) => s.id === sessionIdRef.current)?.messages || [];
    const existingMessage = sessionMessages.find(
      (m) => m.id === lastMessage.id
    );

    if (existingMessage) {
      // Update existing message
      if (existingMessage.content !== lastMessage.content) {
        updateMessage({
          sessionId: sessionIdRef.current,
          messageId: lastMessage.id,
          updates: {
            content: lastMessage.content,
          },
        });
      }
    } else {
      // Add new message
      const role = lastMessage.role.toUpperCase() as MessageRole;

      addMessage({
        sessionId: sessionIdRef.current,
        message: {
          id: lastMessage.id,
          role,
          content: lastMessage.content,
          createdAt: new Date(),
        },
      });
    }
  }, [aiSdkMessages, sessions, addMessage, updateMessage]);

  // Handle sending a user message
  const sendMessage = useCallback(
    (content: string, attachments: string[] = []) => {
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
      setAgentStatus({
        sessionId: sessionIdRef.current,
        status: "thinking",
        message: "Thinking...",
      });

      // Create a unique ID for this message
      const messageId = uuidv4();

      // Add the user message to our store
      addMessage({
        sessionId: sessionIdRef.current,
        message: {
          id: messageId,
          role: "USER",
          content,
          attachments,
          createdAt: new Date(),
        },
      });

      // Submit the message through AI SDK
      // This will trigger the AI response
      const submitEvent = {
        preventDefault: () => {},
        currentTarget: {
          elements: {
            // Create a mock form with the message as input
            input: {
              value: content,
            },
          },
        },
      } as unknown as React.FormEvent<HTMLFormElement>;

      handleSubmit(submitEvent);
    },
    [addMessage, handleSubmit, setAgentStatus, isInitialized, isAuthenticated, isApiKeyValid]
  );

  // Handle stopping the generation
  const stopGeneration = useCallback(() => {
    stop();
    cancelStream(sessionIdRef.current);
    setAgentStatus({
      sessionId: sessionIdRef.current,
      status: "idle",
      message: "",
    });
  }, [stop, cancelStream, setAgentStatus]);

  return {
    // Chat state
    sessionId: sessionIdRef.current,
    messages:
      sessions.find((s) => s.id === sessionIdRef.current)?.messages || [],
    isLoading,
    error: error || authError || storeAuthError,

    // Auth state
    isAuthenticated,
    isInitialized,
    isApiKeyValid,
    authError: authError || storeAuthError,

    // Tool call state
    activeToolCalls: Array.from(activeToolCalls.values()),
    toolResults: Array.from(toolResults.values()),

    // Input state (from AI SDK)
    input,
    handleInputChange,

    // Actions
    sendMessage,
    stopGeneration,
    reload,
    
    // Tool call actions
    retryToolCall,
    cancelToolCall,
  };
}
