"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  Bot,
  Brain,
  CheckCircle2,
  Clock,
  Copy,
  Info,
  MoreHorizontal,
  Shield,
  Sparkles,
  User,
  Zap,
} from "lucide-react";
import { startTransition, useCallback, useMemo } from "react";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

function RoleAvatar({
  config,
  isAssistant,
  isUser,
  isSystem,
  isTool,
  timeDisplay,
}: {
  config: ReturnType<typeof useMemo> extends infer T ? any : any;
  isAssistant: boolean;
  isUser: boolean;
  isSystem: boolean;
  isTool: boolean;
  timeDisplay: { relative: string; absolute: string } | null;
}) {
  const IconComponent = (config as any).icon;

  return (
    <HoverCard>
      <HoverCardTrigger asChild>
        <motion.div
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          transition={{ duration: 0.2 }}
        >
          <Avatar
            className={cn(
              "h-10 w-10 relative overflow-visible cursor-pointer",
              "border-2 border-transparent hover:border-primary/20",
              "transition-all duration-300"
            )}
          >
            <motion.div
              className={cn(
                "w-full h-full flex items-center justify-center rounded-full",
                (config as any).className
              )}
              whileHover={{ rotate: isAssistant ? 360 : 0 }}
              transition={{ duration: 0.6 }}
            >
              <IconComponent className="h-5 w-5" />
            </motion.div>
            <motion.div
              className="absolute -bottom-1 -right-1"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.3, duration: 0.3 }}
            >
              <div
                className={cn(
                  "w-4 h-4 rounded-full border-2 border-background flex items-center justify-center",
                  isAssistant && "bg-emerald-500",
                  isUser && "bg-blue-500",
                  isSystem && "bg-yellow-500",
                  isTool && "bg-purple-500"
                )}
              >
                {isAssistant && <Sparkles className="w-2 h-2 text-white" />}
                {isUser && <CheckCircle2 className="w-2 h-2 text-white" />}
                {isSystem && <Shield className="w-2 h-2 text-white" />}
                {isTool && <Zap className="w-2 h-2 text-white" />}
              </div>
            </motion.div>
          </Avatar>
        </motion.div>
      </HoverCardTrigger>
      <HoverCardContent className="w-64">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "w-8 h-8 rounded-full bg-linear-to-r flex items-center justify-center",
                `bg-linear-to-r ${(config as any).gradient}`
              )}
            >
              <IconComponent className="w-4 h-4 text-white" />
            </div>
            <div>
              <h4 className="font-medium">{(config as any).hoverText}</h4>
              <Badge variant={(config as any).badgeVariant} className="text-xs">
                {(config as any).badgeText}
              </Badge>
            </div>
          </div>
          {isAssistant && (
            <div className="text-sm text-muted-foreground">
              <p>TripSage AI assistant powered by cutting-edge language models</p>
              <div className="flex items-center gap-1 mt-2">
                <Brain className="w-3 h-3" />
                <span className="text-xs">Context-aware • Travel expertise</span>
              </div>
            </div>
          )}
          {timeDisplay && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Clock className="w-3 h-3" />
              <span>{timeDisplay.absolute}</span>
            </div>
          )}
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}

function partsToText(parts?: { type: string; text?: string }[]): string | undefined {
  if (!parts) return undefined;
  try {
    return parts
      .filter((p) => p && p.type === "text" && typeof p.text === "string")
      .map((p) => p.text as string)
      .join("");
  } catch {
    return undefined;
  }
}

import type { Message, ToolCall, ToolResult } from "@/types/chat";
import { MessageAttachments } from "./message-attachments";
import { MessageBubble } from "./message-bubble";
import { MessageToolCalls } from "./message-tool-calls";

interface MessageItemProps {
  message: Message;
  activeToolCalls?: ToolCall[];
  toolResults?: ToolResult[];
  onRetryToolCall?: (toolCallId: string) => void;
  onCancelToolCall?: (toolCallId: string) => void;
  isStreaming?: boolean;
  showActions?: boolean;
}

export function MessageItem({
  message,
  activeToolCalls: _activeToolCalls,
  toolResults,
  onRetryToolCall,
  onCancelToolCall,
  isStreaming = false,
  showActions = true,
}: MessageItemProps) {
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";
  const isSystem = message.role === "system";
  const isTool = false; // 'tool' role not supported in current Message type

  const hasAttachments = message.attachments && message.attachments.length > 0;
  const hasToolCalls = message.toolCalls && message.toolCalls.length > 0;

  // Timestamp formatting with relative time
  const timeDisplay = useMemo(() => {
    if (!message.createdAt) return null;

    const date = new Date(message.createdAt);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    let relative = "";
    if (diffMins < 1) relative = "Just now";
    else if (diffMins < 60) relative = `${diffMins}m ago`;
    else if (diffHours < 24) relative = `${diffHours}h ago`;
    else if (diffDays < 7) relative = `${diffDays}d ago`;
    else relative = date.toLocaleDateString();

    const absolute = date.toLocaleString([], {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

    return { relative, absolute };
  }, [message.createdAt]);

  // avatar configuration with role-based styling
  const avatarConfig = useMemo(() => {
    if (isUser) {
      return {
        icon: User,
        className: "bg-primary text-primary-foreground",
        gradient: "from-blue-500 to-purple-600",
        badgeText: "You",
        badgeVariant: "default" as const,
        hoverText: "Your message",
      };
    }

    if (isAssistant) {
      return {
        icon: Bot,
        className:
          "bg-linear-to-br from-emerald-500/20 to-blue-500/20 text-emerald-600 dark:text-emerald-400",
        gradient: "from-emerald-500 to-blue-500",
        badgeText: "AI",
        badgeVariant: "secondary" as const,
        hoverText: "TripSage AI Assistant",
      };
    }

    if (isSystem) {
      return {
        icon: Shield,
        className:
          "bg-linear-to-br from-yellow-500/20 to-orange-500/20 text-yellow-600 dark:text-yellow-400",
        gradient: "from-yellow-500 to-orange-500",
        badgeText: "System",
        badgeVariant: "outline" as const,
        hoverText: "System notification",
      };
    }

    if (isTool) {
      return {
        icon: Activity,
        className:
          "bg-linear-to-br from-purple-500/20 to-pink-500/20 text-purple-600 dark:text-purple-400",
        gradient: "from-purple-500 to-pink-500",
        badgeText: "Tool",
        badgeVariant: "outline" as const,
        hoverText: "Tool execution result",
      };
    }

    return {
      icon: Info,
      className: "bg-muted text-muted-foreground",
      gradient: "from-gray-500 to-gray-600",
      badgeText: "Unknown",
      badgeVariant: "outline" as const,
      hoverText: "Unknown message type",
    };
  }, [isUser, isAssistant, isSystem, isTool]);

  // Handle copy message content
  const handleCopyMessage = useCallback(() => {
    const content = partsToText((message as any).parts) ?? message.content;
    if (!content) return;
    startTransition(() => {
      navigator.clipboard.writeText(content);
    });
  }, [message]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -20, scale: 0.95 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      layout="position"
      className={cn(
        "group flex w-full gap-4 items-start relative",
        "hover:bg-muted/30 rounded-lg p-2 -m-2 transition-all duration-300",
        isUser && "justify-end"
      )}
    >
      {/* Assistant/System/Tool avatar */}
      {!isUser && (
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.1, duration: 0.3 }}
        >
          <RoleAvatar
            config={avatarConfig}
            isAssistant={isAssistant}
            isUser={isUser}
            isSystem={isSystem}
            isTool={isTool}
            timeDisplay={timeDisplay}
          />
        </motion.div>
      )}

      {/* Message content container */}
      <motion.div
        className={cn("flex flex-col max-w-[85%] min-w-0", isUser && "items-end")}
        layout="position"
      >
        {/* Role badge for non-user messages */}
        {!isUser && (
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2, duration: 0.3 }}
            className="mb-1"
          >
            <Badge variant={avatarConfig.badgeVariant} className="text-xs px-2 py-0.5">
              {avatarConfig.badgeText}
            </Badge>
          </motion.div>
        )}

        {/* Message content */}
        <motion.div className="flex flex-col gap-2 w-full" layout="position">
          <AnimatePresence>
            {hasAttachments && message.attachments && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
              >
                <MessageAttachments
                  attachments={message.attachments.map((a) => a.url)}
                />
              </motion.div>
            )}
          </AnimatePresence>

          <motion.div whileHover={{ scale: 1.01 }} transition={{ duration: 0.2 }}>
            <MessageBubble message={message} isStreaming={isStreaming} />
          </motion.div>

          <AnimatePresence>
            {hasToolCalls && message.toolCalls && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
              >
                <MessageToolCalls
                  toolCalls={message.toolCalls}
                  toolResults={message.toolResults || toolResults}
                  onRetryToolCall={onRetryToolCall}
                  onCancelToolCall={onCancelToolCall}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* timestamp and actions */}
        <motion.div
          className={cn(
            "flex items-center gap-2 mt-2 opacity-0 group-hover:opacity-100",
            "transition-opacity duration-300",
            isUser && "flex-row-reverse"
          )}
          initial={{ opacity: 0 }}
          animate={{ opacity: 0 }}
        >
          {timeDisplay && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <motion.div
                    className="flex items-center gap-1 text-xs text-muted-foreground cursor-help"
                    whileHover={{ scale: 1.05 }}
                    transition={{ duration: 0.2 }}
                  >
                    <Clock className="w-3 h-3" />
                    <span>{timeDisplay.relative}</span>
                  </motion.div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{timeDisplay.absolute}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}

          {/* Action buttons */}
          {showActions && message.content && (
            <motion.div
              className="flex items-center gap-1"
              initial={{ opacity: 0, x: isUser ? 10 : -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1, duration: 0.2 }}
            >
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0 hover:bg-primary/10"
                      onClick={handleCopyMessage}
                    >
                      <Copy className="w-3 h-3" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Copy message</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0 hover:bg-primary/10"
                    >
                      <MoreHorizontal className="w-3 h-3" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>More actions</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </motion.div>
          )}
        </motion.div>
      </motion.div>

      {/* User avatar */}
      {isUser && (
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.1, duration: 0.3 }}
        >
          <RoleAvatar
            config={avatarConfig}
            isAssistant={isAssistant}
            isUser={isUser}
            isSystem={isSystem}
            isTool={isTool}
            timeDisplay={timeDisplay}
          />
        </motion.div>
      )}
    </motion.div>
  );
}
