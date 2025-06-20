"use client";

import { Avatar } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { User } from "lucide-react";

interface TypingUser {
  userId: string;
  username?: string;
  timestamp: string;
}

interface TypingIndicatorProps {
  typingUsers: TypingUser[];
  sessionId: string;
  className?: string;
}

export function TypingIndicator({
  typingUsers,
  sessionId: _sessionId,
  className,
}: TypingIndicatorProps) {
  // Filter out old typing indicators (older than 5 seconds)
  const activeTypingUsers = typingUsers.filter((user) => {
    const timeDiff = Date.now() - new Date(user.timestamp).getTime();
    return timeDiff < 5000; // 5 seconds
  });

  if (activeTypingUsers.length === 0) {
    return null;
  }

  // Format the typing text
  const getTypingText = () => {
    const count = activeTypingUsers.length;
    const names = activeTypingUsers
      .map((user) => user.username || `User ${user.userId.slice(-4)}`)
      .slice(0, 3); // Show max 3 names

    if (count === 1) {
      return `${names[0]} is typing...`;
    }
    if (count === 2) {
      return `${names[0]} and ${names[1]} are typing...`;
    }
    if (count === 3) {
      return `${names[0]}, ${names[1]}, and ${names[2]} are typing...`;
    }
    return `${names[0]}, ${names[1]}, and ${count - 2} others are typing...`;
  };

  return (
    <div className={cn("flex items-center gap-3 px-4 py-2", className)}>
      {/* User avatars */}
      <div className="flex -space-x-2">
        {activeTypingUsers.slice(0, 3).map((user) => (
          <Avatar
            key={user.userId}
            className="h-6 w-6 border-2 border-background bg-secondary"
          >
            <User className="h-3 w-3" />
          </Avatar>
        ))}
      </div>

      {/* Typing text and animated dots */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">{getTypingText()}</span>

        {/* Animated typing dots */}
        <div className="flex items-center space-x-1">
          <div className="typing-dot" />
          <div className="typing-dot animation-delay-200" />
          <div className="typing-dot animation-delay-400" />
        </div>
      </div>

      <style jsx>{`
        .typing-dot {
          width: 4px;
          height: 4px;
          background-color: hsl(var(--muted-foreground));
          border-radius: 50%;
          animation: typing-bounce 1.4s ease-in-out infinite both;
        }

        .animation-delay-200 {
          animation-delay: 0.2s;
        }

        .animation-delay-400 {
          animation-delay: 0.4s;
        }

        @keyframes typing-bounce {
          0%,
          80%,
          100% {
            transform: scale(0.8);
            opacity: 0.5;
          }
          40% {
            transform: scale(1);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}
