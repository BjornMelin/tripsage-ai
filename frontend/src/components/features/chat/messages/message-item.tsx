'use client';

import React from 'react';
import { type Message, MessageRole } from '@/types/chat';
import { cn } from '@/lib/utils';
import { Avatar } from '@/components/ui/avatar';
import { Bot, User, Info, Server } from 'lucide-react';
import MessageBubble from './message-bubble';
import MessageAttachments from './message-attachments';
import MessageToolCalls from './message-tool-calls';

interface MessageItemProps {
  message: Message;
}

export default function MessageItem({ message }: MessageItemProps) {
  const isUser = message.role === 'USER';
  const isAssistant = message.role === 'ASSISTANT';
  const isSystem = message.role === 'SYSTEM';
  const isTool = message.role === 'TOOL';
  
  const hasAttachments = message.attachments && message.attachments.length > 0;
  const hasToolCalls = message.toolCalls && message.toolCalls.length > 0;
  
  // Format timestamp
  const formattedTime = message.createdAt 
    ? new Date(message.createdAt).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      })
    : '';

  // Get the avatar icon based on message role
  const getAvatarIcon = () => {
    if (isAssistant) return <Bot className="h-4 w-4" />;
    if (isSystem) return <Info className="h-4 w-4" />;
    if (isTool) return <Server className="h-4 w-4" />;
    return <span className="text-xs">SYS</span>;
  };

  // Get the avatar background color based on message role
  const getAvatarClass = () => {
    if (isAssistant) return "bg-secondary";
    if (isSystem) return "bg-yellow-500/20"; 
    if (isTool) return "bg-blue-500/20";
    return "bg-secondary";
  };

  return (
    <div
      className={cn(
        "flex w-full gap-4 items-start",
        isUser && "justify-end"
      )}
    >
      {!isUser && (
        <Avatar className={cn(
          "h-8 w-8 flex items-center justify-center",
          getAvatarClass()
        )}>
          {getAvatarIcon()}
        </Avatar>
      )}
      
      <div className={cn(
        "flex flex-col max-w-[85%]",
        isUser && "items-end"
      )}>
        <div className="flex flex-col gap-2">
          {hasAttachments && (
            <MessageAttachments attachments={message.attachments!} />
          )}
          
          <MessageBubble message={message} />
          
          {hasToolCalls && (
            <MessageToolCalls 
              toolCalls={message.toolCalls!} 
              toolResults={message.toolResults} 
            />
          )}
        </div>
        
        {formattedTime && (
          <span className="text-xs text-muted-foreground mt-1">
            {formattedTime}
          </span>
        )}
      </div>
      
      {isUser && (
        <Avatar className="h-8 w-8 bg-primary flex items-center justify-center">
          <User className="h-4 w-4 text-primary-foreground" />
        </Avatar>
      )}
    </div>
  );
}