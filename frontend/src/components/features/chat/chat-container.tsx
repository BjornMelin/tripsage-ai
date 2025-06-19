"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useChatAi } from "@/hooks/use-chat-ai";
import { cn } from "@/lib/utils";
import { useAuthStore, useChatStore } from "@/stores";
import type { Message } from "@/types/chat";
import { AlertCircle, Key, PanelRightOpen, Wifi } from "lucide-react";
import Link from "next/link";
import React, { useCallback, useEffect, useOptimistic, startTransition } from "react";
import { AgentStatusPanel } from "./agent-status-panel";
import { ConnectionStatus } from "../shared/connection-status";
import { MessageInput } from "./message-input";
import { MessageList } from "./messages/message-list";

interface ChatContainerProps {
  sessionId?: string;
  initialMessages?: Message[];
  className?: string;
}

export function ChatContainer({
  sessionId,
  initialMessages = [],
  className,
}: ChatContainerProps) {
  const [showAgentPanel, setShowAgentPanel] = React.useState(false);

  // Use our new chat hook that integrates Vercel AI SDK
  const {
    sessionId: chatSessionId,
    messages: baseMessages,
    isLoading,
    error,
    input,
    handleInputChange,
    sendMessage,
    stopGeneration,
    isAuthenticated,
    isInitialized,
    isApiKeyValid,
    authError,
    // Tool call functionality
    activeToolCalls,
    toolResults,
    retryToolCall,
    cancelToolCall,
  } = useChatAi({
    sessionId,
    initialMessages,
  });

  // Transform messages to ensure they have the correct type
  const typedMessages: Message[] = baseMessages.map((msg: any) => ({
    ...msg,
    createdAt: msg.createdAt || msg.timestamp || new Date().toISOString(),
  }));

  // React 19 optimistic updates for instant message display
  const [optimisticMessages, addOptimisticMessage] = useOptimistic(
    typedMessages,
    (state: Message[], newMessage: Message) => [...state, newMessage]
  );

  // Get chat store state including WebSocket status
  const {
    connectionStatus,
    isRealtimeEnabled,
    connectWebSocket,
    disconnectWebSocket,
    setRealtimeEnabled,
    isStreaming,
  } = useChatStore((state) => ({
    connectionStatus: state.connectionStatus,
    isRealtimeEnabled: state.isRealtimeEnabled,
    connectWebSocket: state.connectWebSocket,
    disconnectWebSocket: state.disconnectWebSocket,
    setRealtimeEnabled: state.setRealtimeEnabled,
    isStreaming: state.isStreaming,
  }));

  // Track connection toggle state
  const [showConnectionStatus, setShowConnectionStatus] = React.useState(false);

  // Handle sending messages with React 19 optimistic updates
  const handleSendMessage = useCallback(
    (content: string, attachments: string[] = []) => {
      // Convert string URLs to Attachment objects
      const attachmentObjects = attachments.map((url, index) => ({
        id: `temp-attachment-${index}`,
        url,
        name: url.split("/").pop() || "Attachment",
      }));

      // Create optimistic message for instant UI feedback
      const optimisticMessage: Message = {
        id: `temp-${Date.now()}`,
        role: "user",
        content,
        createdAt: new Date().toISOString(),
        attachments: attachmentObjects,
      };

      // Add optimistic message immediately
      addOptimisticMessage(optimisticMessage);

      // Use startTransition for better performance
      startTransition(() => {
        sendMessage(content, attachmentObjects);
      });
    },
    [sendMessage, addOptimisticMessage]
  );

  // Handle cancel
  const handleCancel = useCallback(() => {
    stopGeneration();
  }, [stopGeneration]);

  // Get auth token from auth store
  const { tokenInfo } = useAuthStore((state) => ({
    tokenInfo: state.tokenInfo,
  }));

  // Handle WebSocket connection
  const handleConnectWebSocket = useCallback(async () => {
    if (chatSessionId && isAuthenticated && tokenInfo?.accessToken) {
      try {
        await connectWebSocket(chatSessionId, tokenInfo.accessToken);
      } catch (error) {
        console.error("Failed to connect WebSocket:", error);
      }
    }
  }, [chatSessionId, isAuthenticated, tokenInfo?.accessToken, connectWebSocket]);

  // Auto-connect WebSocket when session is ready
  useEffect(() => {
    if (
      isRealtimeEnabled &&
      chatSessionId &&
      isAuthenticated &&
      connectionStatus === "disconnected"
    ) {
      handleConnectWebSocket();
    }
  }, [
    isRealtimeEnabled,
    chatSessionId,
    isAuthenticated,
    connectionStatus,
    handleConnectWebSocket,
  ]);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      disconnectWebSocket();
    };
  }, [disconnectWebSocket]);

  // Show authentication required UI
  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="p-8 text-center max-w-md">
          <AlertCircle className="h-12 w-12 text-orange-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Authentication Required</h3>
          <p className="text-muted-foreground mb-6">
            Please log in to start chatting with TripSage AI.
          </p>
          <Link href="/login">
            <Button className="w-full">Sign In</Button>
          </Link>
        </div>
      </div>
    );
  }

  // Show API key required UI
  if (isAuthenticated && !isApiKeyValid) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="p-8 text-center max-w-md">
          <Key className="h-12 w-12 text-blue-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">API Key Required</h3>
          <p className="text-muted-foreground mb-6">
            A valid OpenAI API key is required to use the chat feature. Please add one
            to get started.
          </p>
          <Link href="/settings/api-keys">
            <Button className="w-full">Manage API Keys</Button>
          </Link>
        </div>
      </div>
    );
  }

  // Show loading UI while initializing
  if (!isInitialized || !chatSessionId) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="p-4 text-center">
          <p>Initializing chat session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col h-full relative", className)}>
      {/* Main chat area */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <MessageList
          messages={optimisticMessages}
          isStreaming={isStreaming}
          sessionId={chatSessionId}
          activeToolCalls={activeToolCalls}
          toolResults={toolResults}
          onRetryToolCall={retryToolCall}
          onCancelToolCall={cancelToolCall}
        />

        <MessageInput
          disabled={isLoading && !isStreaming}
          placeholder="Send a message..."
          value={input}
          onChange={handleInputChange}
          onSend={handleSendMessage}
          onCancel={handleCancel}
          isStreaming={isStreaming}
        />
      </div>

      {/* Connection status toggle */}
      <Button
        variant="outline"
        size="icon"
        className={cn(
          "absolute bottom-32 right-4 h-8 w-8 rounded-full shadow-md",
          connectionStatus === "connected" && "bg-green-500/10 border-green-500/20",
          connectionStatus === "error" && "bg-red-500/10 border-red-500/20"
        )}
        onClick={() => setShowConnectionStatus(!showConnectionStatus)}
        title={`Connection: ${connectionStatus}`}
      >
        <Wifi
          className={cn(
            "h-4 w-4",
            connectionStatus === "connected" && "text-green-500",
            connectionStatus === "error" && "text-red-500",
            connectionStatus === "connecting" && "text-blue-500 animate-pulse"
          )}
        />
      </Button>

      {/* Agent status panel toggle */}
      <Button
        variant="outline"
        size="icon"
        className="absolute bottom-20 right-4 h-8 w-8 rounded-full shadow-md"
        onClick={() => setShowAgentPanel(!showAgentPanel)}
      >
        <PanelRightOpen
          className={cn("h-4 w-4 transition-transform", showAgentPanel && "rotate-180")}
        />
      </Button>

      {/* Connection status panel */}
      {showConnectionStatus && (
        <div className="absolute bottom-32 right-16 w-80">
          <ConnectionStatus
            status={connectionStatus}
            onReconnect={handleConnectWebSocket}
          />

          {/* Real-time toggle */}
          <div className="mt-2 p-3 bg-background border rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-sm font-medium">Real-time messaging</span>
                <p className="text-xs text-muted-foreground">
                  Enable for instant typing indicators and live updates
                </p>
              </div>
              <Button
                variant={isRealtimeEnabled ? "default" : "outline"}
                size="sm"
                onClick={() => setRealtimeEnabled(!isRealtimeEnabled)}
              >
                {isRealtimeEnabled ? "On" : "Off"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Agent status panel */}
      {showAgentPanel && (
        <div className="absolute bottom-20 right-16 w-72">
          <AgentStatusPanel sessionId={chatSessionId} />
        </div>
      )}

      {/* Error display */}
      {(error || authError) && (
        <div className="absolute top-2 left-1/2 transform -translate-x-1/2 z-50 max-w-md">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {authError ||
                (error instanceof Error ? error.message : String(error || ""))}
              {authError?.includes("API key") && (
                <div className="mt-2">
                  <Link href="/settings/api-keys">
                    <Button variant="outline" size="sm">
                      Manage API Keys
                    </Button>
                  </Link>
                </div>
              )}
            </AlertDescription>
          </Alert>
        </div>
      )}
    </div>
  );
}
