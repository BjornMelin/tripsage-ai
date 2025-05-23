"use client";

import React, { useCallback, useEffect } from "react";
import { useChatStore } from "@/stores";
import MessageList from "./messages/message-list";
import MessageInput from "./message-input";
import AgentStatusPanel from "./agent-status-panel";
import { PanelRightOpen, AlertCircle, Key } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import type { Message } from "@/types/chat";
import { useChatAi } from "@/hooks/use-chat-ai";
import Link from "next/link";

interface ChatContainerProps {
  sessionId?: string;
  initialMessages?: Message[];
  className?: string;
}

export default function ChatContainer({
  sessionId,
  initialMessages = [],
  className,
}: ChatContainerProps) {
  const [showAgentPanel, setShowAgentPanel] = React.useState(false);

  // Use our new chat hook that integrates Vercel AI SDK
  const {
    sessionId: chatSessionId,
    messages,
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
  } = useChatAi({
    sessionId,
    initialMessages,
  });

  // Get streaming status from chat store
  const { agentStatus, isStreaming } = useChatStore((state) => ({
    agentStatus: state.getAgentStatus(chatSessionId),
    isStreaming: state.isStreaming(chatSessionId),
  }));

  // Handle sending messages
  const handleSendMessage = useCallback(
    (content: string, attachments: string[] = []) => {
      sendMessage(content, attachments);
    },
    [sendMessage]
  );

  // Handle cancel
  const handleCancel = useCallback(() => {
    stopGeneration();
  }, [stopGeneration]);

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
            A valid OpenAI API key is required to use the chat feature. Please add one to get started.
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
        <MessageList messages={messages} isStreaming={isStreaming} />

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

      {/* Agent status panel toggle */}
      <Button
        variant="outline"
        size="icon"
        className="absolute bottom-20 right-4 h-8 w-8 rounded-full shadow-md"
        onClick={() => setShowAgentPanel(!showAgentPanel)}
      >
        <PanelRightOpen
          className={cn(
            "h-4 w-4 transition-transform",
            showAgentPanel && "rotate-180"
          )}
        />
      </Button>

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
              {authError || (error?.message || String(error))}
              {authError && authError.includes("API key") && (
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
