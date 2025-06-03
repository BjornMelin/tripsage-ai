"use client";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { memo } from "react";

export interface TypingIndicatorProps {
  users: string[];
  className?: string;
}

export const TypingIndicator = memo(function TypingIndicator({
  users,
  className,
}: TypingIndicatorProps) {
  if (users.length === 0) {
    return null;
  }

  const getTypingText = () => {
    if (users.length === 1) {
      return `${users[0]} is typing...`;
    } else if (users.length === 2) {
      return `${users[0]} and ${users[1]} are typing...`;
    } else if (users.length === 3) {
      return `${users[0]}, ${users[1]}, and ${users[2]} are typing...`;
    } else {
      return `${users[0]}, ${users[1]}, and ${users.length - 2} others are typing...`;
    }
  };

  return (
    <div
      className={cn(
        "flex items-center gap-3 px-4 py-2 text-sm text-muted-foreground",
        className
      )}
    >
      <Avatar className="h-6 w-6">
        <AvatarFallback className="text-xs">
          {users[0]?.charAt(0).toUpperCase()}
        </AvatarFallback>
      </Avatar>

      <div className="flex items-center gap-2">
        <span>{getTypingText()}</span>

        {/* Animated typing dots */}
        <div className="flex gap-1">
          <div className="w-1 h-1 bg-current rounded-full animate-bounce [animation-delay:-0.3s]" />
          <div className="w-1 h-1 bg-current rounded-full animate-bounce [animation-delay:-0.15s]" />
          <div className="w-1 h-1 bg-current rounded-full animate-bounce" />
        </div>
      </div>
    </div>
  );
});
