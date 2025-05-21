'use client';

import React from 'react';
import { Message } from '@/types/chat';
import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
}

export default function MessageBubble({ 
  message, 
  isStreaming = false 
}: MessageBubbleProps) {
  const isUser = message.role === 'USER';
  const isAssistant = message.role === 'ASSISTANT';
  const isSystem = message.role === 'SYSTEM';
  const isTool = message.role === 'TOOL';
  
  // Empty fallback content
  const emptyContent = isUser ? "..." : "_";
  
  return (
    <div
      className={cn(
        "py-2 px-3 rounded-lg relative",
        isUser && "bg-primary text-primary-foreground",
        isAssistant && "bg-card border",
        isSystem && "bg-yellow-500/20 border border-yellow-500/50",
        isTool && "bg-blue-500/10 border border-blue-500/30",
        isStreaming && "animate-pulse"
      )}
    >
      {isStreaming && (
        <div className="absolute -right-2 -top-2">
          <Loader2 className="h-4 w-4 animate-spin" />
        </div>
      )}
      
      <div className="prose prose-sm dark:prose-invert max-w-none break-words">
        <ReactMarkdown components={{
          // Override pre to add proper styling for code blocks
          pre: ({ node, ...props }) => (
            <pre
              className="bg-muted p-2 rounded-md overflow-x-auto"
              {...props}
            />
          ),
          // Override code to add proper styling for inline code
          code: ({ node, inline, ...props }) => (
            inline ? 
              <code className="bg-muted px-1 py-0.5 rounded-sm text-sm" {...props} /> :
              <code {...props} />
          ),
          // Proper link styling
          a: ({ node, ...props }) => (
            <a
              className="text-primary underline hover:text-primary/80"
              target="_blank"
              rel="noopener noreferrer"
              {...props}
            />
          ),
        }}>
          {message.content || emptyContent}
        </ReactMarkdown>
      </div>
    </div>
  );
}