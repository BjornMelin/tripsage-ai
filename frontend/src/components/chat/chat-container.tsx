"use client";

import { MessageCircle, Settings, Users } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useOptimisticChat } from "@/hooks/use-optimistic-chat";
import { useWebSocketChat } from "@/hooks/use-websocket-chat";
import { cn } from "@/lib/utils";
import { CompactConnectionStatus } from "../features/shared/connection-status";
import { MessageInput } from "./message-input";
import { MessageList } from "./message-list";

export interface ChatContainerProps {
  currentUser: {
    id: string;
    name: string;
    avatar?: string;
  };
  className?: string;
  title?: string;
  showHeader?: boolean;
}

export function ChatContainer({
  currentUser,
  className,
  title = "AI Travel Assistant",
  showHeader = true,
}: ChatContainerProps) {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // WebSocket chat hook with real-time messaging
  const {
    messages,
    connectionStatus,
    sendMessage,
    isConnected,
    reconnect,
    typingUsers,
    startTyping,
    stopTyping,
  } = useWebSocketChat({ autoConnect: true });

  // Optimistic updates for better UX
  const { optimisticMessages, sendOptimisticMessage, isPending, error } =
    useOptimisticChat({
      messages,
      sendMessage,
      currentUser,
    });

  // Demo: Add some sample messages for development
  // TODO: Remove this in production
  const demoMessages =
    messages.length === 0
      ? [
          {
            id: "demo-1",
            content:
              "Hello! I'm your AI travel assistant. I can help you plan amazing trips, find the best deals, and create personalized itineraries. What destination are you thinking about?",
            timestamp: new Date(Date.now() - 5 * 60 * 1000),
            sender: {
              id: "ai-assistant",
              name: "TripSage AI",
              avatar: undefined,
            },
            status: "sent" as const,
            type: "text" as const,
          },
        ]
      : [];

  const allMessages = [...demoMessages, ...optimisticMessages];

  return (
    <Card className={cn("flex flex-col h-full max-h-[600px]", className)}>
      {showHeader && (
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                <MessageCircle className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold">{title}</h3>
                <div className="flex items-center gap-2">
                  <CompactConnectionStatus
                    status={connectionStatus}
                    onReconnect={reconnect}
                  />
                  {typingUsers.length > 0 && (
                    <Badge variant="secondary" className="text-xs">
                      AI is typing...
                    </Badge>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsSettingsOpen(!isSettingsOpen)}
              >
                <Settings className="h-4 w-4" />
                <span className="sr-only">Chat settings</span>
              </Button>

              <Badge variant="outline" className="text-xs">
                <Users className="h-3 w-3 mr-1" />
                {isConnected ? "Online" : "Offline"}
              </Badge>
            </div>
          </div>

          {error && (
            <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-800 dark:bg-red-950 dark:border-red-800 dark:text-red-200">
              Failed to send message: {error}
            </div>
          )}
        </CardHeader>
      )}

      <CardContent className="flex flex-col flex-1 p-0 min-h-0">
        {/* Messages area */}
        <div className="flex-1 min-h-0">
          <MessageList
            messages={allMessages}
            currentUserId={currentUser.id}
            typingUsers={typingUsers}
            connectionStatus={connectionStatus}
            onReconnect={reconnect}
          />
        </div>

        {/* Message input */}
        <MessageInput
          onSendMessage={sendOptimisticMessage}
          onStartTyping={startTyping}
          onStopTyping={stopTyping}
          disabled={!isConnected || isPending}
          placeholder={
            !isConnected
              ? "Reconnecting..."
              : isPending
                ? "Sending..."
                : "Ask me about travel plans, destinations, or anything else..."
          }
        />
      </CardContent>
    </Card>
  );
}
