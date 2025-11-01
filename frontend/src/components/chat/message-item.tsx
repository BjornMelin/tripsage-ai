"use client";

import { CheckCircle, Clock, MoreVertical, XCircle } from "lucide-react";
import { memo } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { OptimisticChatMessage } from "@/hooks/use-optimistic-chat";
import { cn } from "@/lib/utils";

export interface MessageItemProps {
  message: OptimisticChatMessage;
  isOwn: boolean;
  showAvatar?: boolean;
  showTimestamp?: boolean;
  className?: string;
}

export const MessageItem = memo(function MessageItem({
  message,
  isOwn,
  showAvatar = true,
  showTimestamp = true,
  className,
}: MessageItemProps) {
  const getStatusIcon = () => {
    switch (message.status) {
      case "sending":
        return <Clock className="h-3 w-3 text-muted-foreground" />;
      case "sent":
        return <CheckCircle className="h-3 w-3 text-green-500" />;
      case "failed":
        return <XCircle className="h-3 w-3 text-red-500" />;
      default:
        return null;
    }
  };

  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(date);
  };

  return (
    <div
      className={cn(
        "group flex gap-3 px-4 py-2 hover:bg-muted/30 transition-colors",
        isOwn && "justify-end",
        className
      )}
    >
      {showAvatar && !isOwn && (
        <Avatar className="h-8 w-8 mt-1">
          <AvatarImage src={message.sender.avatar} alt={message.sender.name} />
          <AvatarFallback className="text-xs">
            {message.sender.name.charAt(0).toUpperCase()}
          </AvatarFallback>
        </Avatar>
      )}

      <div className={cn("flex flex-col space-y-1 max-w-[70%]", isOwn && "items-end")}>
        {!isOwn && showAvatar && (
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-foreground">
              {message.sender.name}
            </span>
            {showTimestamp && (
              <span className="text-xs text-muted-foreground">
                {formatTime(message.timestamp)}
              </span>
            )}
          </div>
        )}

        <Card
          className={cn(
            "px-3 py-2 max-w-full wrap-break-word",
            isOwn
              ? "bg-primary text-primary-foreground border-primary"
              : "bg-muted border-muted-foreground/20",
            message.isOptimistic && "opacity-70",
            message.status === "failed" &&
              "bg-red-50 border-red-200 text-red-800 dark:bg-red-950 dark:border-red-800 dark:text-red-200"
          )}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        </Card>

        <div
          className={cn(
            "flex items-center gap-2",
            isOwn ? "justify-end" : "justify-start"
          )}
        >
          {isOwn && showTimestamp && (
            <span className="text-xs text-muted-foreground">
              {formatTime(message.timestamp)}
            </span>
          )}

          {isOwn && getStatusIcon()}

          {message.status === "failed" && (
            <Button variant="ghost" size="sm" className="h-6 px-2 text-xs">
              Retry
            </Button>
          )}
        </div>
      </div>

      {showAvatar && isOwn && (
        <Avatar className="h-8 w-8 mt-1">
          <AvatarImage src={message.sender.avatar} alt={message.sender.name} />
          <AvatarFallback className="text-xs">
            {message.sender.name.charAt(0).toUpperCase()}
          </AvatarFallback>
        </Avatar>
      )}

      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <MoreVertical className="h-3 w-3" />
      </Button>
    </div>
  );
});
