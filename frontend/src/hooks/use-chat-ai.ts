import { useChat, type Message as AiMessage } from "ai/react";
import { useCallback, useEffect, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import { useChatStore } from "@/stores/chat-store";
import type { Message, MessageRole, ChatSession } from "@/types/chat";

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

  // Ensure the session exists
  useEffect(() => {
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
    sessions,
    activeSessionId,
    setActiveSessionId,
    createSession,
    initialMessages,
    onNewSession,
  ]);

  // Convert our messages to AI SDK format
  const aiMessages: AiMessage[] =
    sessions
      .find((s) => s.id === sessionIdRef.current)
      ?.messages.map((msg) => ({
        id: msg.id,
        role: msg.role.toLowerCase() as "user" | "assistant" | "system",
        content: msg.content,
      })) || [];

  // Set up Vercel AI SDK chat
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
    onResponse: (response) => {
      // Check for rate limit headers
      const retryAfter = response.headers.get("X-RateLimit-Reset");
      if (response.status === 429 && retryAfter) {
        const resetTime = new Date(parseInt(retryAfter) * 1000);
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
    },
    onFinish: (message) => {
      // Set agent to idle when message is complete
      setAgentStatus({
        sessionId: sessionIdRef.current,
        status: "idle",
        message: "",
      });
    },
    onError: (error) => {
      console.error("Chat error:", error);
      
      // Parse error for specific handling
      let errorMessage = "An error occurred while processing your request";
      let errorStatus = "error";
      
      if (error.message) {
        // Check for specific error patterns
        if (error.message.includes("timeout") || error.message.includes("TIMEOUT")) {
          errorMessage = "Request timed out. Please try again.";
          errorStatus = "timeout";
        } else if (error.message.includes("Authentication required") || error.message.includes("AUTH_REQUIRED")) {
          errorMessage = "Authentication required. Please check your API keys.";
          errorStatus = "auth_error";
        } else if (error.message.includes("Rate limited") || error.message.includes("RATE_LIMITED")) {
          errorMessage = "Too many requests. Please wait a moment and try again.";
          errorStatus = "rate_limited";
        } else if (error.message.includes("Service unavailable") || error.message.includes("SERVICE_UNAVAILABLE")) {
          errorMessage = "AI service is temporarily unavailable. Please try again later.";
          errorStatus = "service_unavailable";
        } else if (error.message.includes("Model not available")) {
          errorMessage = "The selected AI model is not available. Please try a different model.";
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
    [addMessage, handleSubmit, setAgentStatus]
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
    error,

    // Input state (from AI SDK)
    input,
    handleInputChange,

    // Actions
    sendMessage,
    stopGeneration,
    reload,
  };
}
