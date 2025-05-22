"use client";

import React, { useCallback, useEffect } from "react";
import { useChatStore } from "@/stores";
import MessageList from "./messages/message-list";
import MessageInput from "./message-input";
import AgentStatusPanel from "./agent-status-panel";
import { PanelRightOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Message } from "@/types/chat";
import { useChatAi } from "@/hooks/use-chat-ai";

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

  if (!chatSessionId) {
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
      {error && (
        <div className="absolute top-2 left-1/2 transform -translate-x-1/2 bg-destructive text-destructive-foreground px-4 py-2 rounded-md text-sm">
          {error.message || String(error)}
        </div>
      )}
    </div>
  );
}
