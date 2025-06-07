"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/stores/chat-store";
import type { Message, ToolCall, ToolResult } from "@/types/chat";
import { AnimatePresence, motion, useSpring, useTransform } from "framer-motion";
import {
  ArrowUp,
  Bot,
  Calendar,
  Camera,
  Compass,
  Copy,
  Gift,
  Globe,
  Loader2,
  MapPin,
  MessageSquare,
  Plane,
  RotateCcw,
  Sparkles,
  Star,
  Volume2,
  Zap,
} from "lucide-react";
import React, { useEffect, useRef, useCallback, useMemo, startTransition } from "react";
import { TypingIndicator } from "../typing-indicator";
import { MessageItem } from "./message-item";

interface MessageListProps {
  messages: Message[];
  isStreaming?: boolean;
  className?: string;
  sessionId?: string;
  activeToolCalls?: ToolCall[];
  toolResults?: ToolResult[];
  onRetryToolCall?: (toolCallId: string) => void;
  onCancelToolCall?: (toolCallId: string) => void;
  onSuggestionClick?: (suggestion: string) => void;
}

export function MessageList({
  messages,
  isStreaming,
  className,
  sessionId,
  activeToolCalls,
  toolResults,
  onRetryToolCall,
  onCancelToolCall,
  onSuggestionClick,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Track if the user has scrolled up (not at the bottom)
  const [userScrolledUp, setUserScrolledUp] = React.useState(false);

  // Get typing users from the store
  const { typingUsers } = useChatStore((state) => ({
    typingUsers: sessionId
      ? Object.values(state.typingUsers).filter((user) =>
          Object.keys(state.typingUsers).find(
            (key) => key.startsWith(`${sessionId}_`) && state.typingUsers[key] === user
          )
        )
      : [],
  }));

  // Scroll to bottom when new messages arrive or content streams
  useEffect(() => {
    if (bottomRef.current && containerRef.current) {
      const container = containerRef.current;

      // Check if user has scrolled up
      const isAtBottom =
        container.scrollHeight - container.clientHeight - container.scrollTop < 100;

      // Auto-scroll if at bottom or a new message arrives from the user
      const lastMessage = messages[messages.length - 1];
      const isNewUserMessage = lastMessage && lastMessage.role === "user";

      if (isAtBottom || isNewUserMessage || isStreaming) {
        bottomRef.current.scrollIntoView({
          behavior: userScrolledUp ? "auto" : "smooth",
        });
        setUserScrolledUp(false);
      }
    }
  }, [messages, messages.length, isStreaming, userScrolledUp]);

  // Advanced suggestion categories with enhanced UX
  const suggestionCategories = useMemo(
    () => [
      {
        title: "Destinations",
        icon: MapPin,
        color: "text-blue-500",
        gradient: "from-blue-500/10 to-cyan-500/10",
        suggestions: [
          {
            text: "Where should I go for a budget-friendly beach vacation?",
            tags: ["Budget", "Beach", "Vacation"],
            difficulty: "Easy",
          },
          {
            text: "What are hidden gems in Southeast Asia for backpackers?",
            tags: ["Adventure", "Backpacking", "Hidden"],
            difficulty: "Medium",
          },
        ],
      },
      {
        title: "Planning",
        icon: Calendar,
        color: "text-green-500",
        gradient: "from-green-500/10 to-emerald-500/10",
        suggestions: [
          {
            text: "Plan a 7-day trip to Japan in spring with cultural experiences.",
            tags: ["Culture", "Japan", "Week-long"],
            difficulty: "Medium",
          },
          {
            text: "Create a family itinerary for Barcelona with kids activities.",
            tags: ["Family", "Kids", "Barcelona"],
            difficulty: "Easy",
          },
        ],
      },
      {
        title: "Experiences",
        icon: Compass,
        color: "text-purple-500",
        gradient: "from-purple-500/10 to-pink-500/10",
        suggestions: [
          {
            text: "Find unique food tours and cooking classes in Italy.",
            tags: ["Food", "Culture", "Italy"],
            difficulty: "Easy",
          },
          {
            text: "Adventure activities for thrill-seekers in New Zealand.",
            tags: ["Adventure", "Extreme", "New Zealand"],
            difficulty: "Hard",
          },
        ],
      },
    ],
    []
  );

  // Memoized scroll handler for better performance
  const handleScroll = useCallback(() => {
    if (containerRef.current) {
      const container = containerRef.current;
      const isAtBottom =
        container.scrollHeight - container.clientHeight - container.scrollTop < 100;
      setUserScrolledUp(!isAtBottom);
    }
  }, []);

  // Enhanced suggestion click handler with optimistic UI
  const handleSuggestionClick = useCallback(
    (suggestion: string) => {
      startTransition(() => {
        onSuggestionClick?.(suggestion);
      });
    },
    [onSuggestionClick]
  );

  const EmptyState = () => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="flex flex-col items-center justify-center h-full py-16 px-6"
    >
      <div className="max-w-4xl w-full space-y-12 text-center">
        {/* Hero section with advanced animations */}
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.8, ease: "easeOut" }}
          className="space-y-6"
        >
          <div className="relative">
            <motion.div
              className="absolute inset-0 flex items-center justify-center"
              animate={{
                background: [
                  "radial-gradient(circle, rgba(59,130,246,0.1) 0%, rgba(147,51,234,0.1) 100%)",
                  "radial-gradient(circle, rgba(147,51,234,0.1) 0%, rgba(59,130,246,0.1) 100%)",
                ],
              }}
              transition={{
                duration: 4,
                repeat: Number.POSITIVE_INFINITY,
                repeatType: "reverse",
              }}
            >
              <div className="w-32 h-32 rounded-full" />
            </motion.div>
            <motion.div
              animate={{
                y: [-5, 5, -5],
                rotate: [-2, 2, -2],
              }}
              transition={{
                duration: 6,
                repeat: Number.POSITIVE_INFINITY,
                ease: "easeInOut",
              }}
            >
              <Bot className="relative w-20 h-20 mx-auto text-primary drop-shadow-lg" />
            </motion.div>
          </div>

          <div className="space-y-4">
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.6 }}
              className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-emerald-600 bg-clip-text text-transparent"
            >
              Welcome to TripSage AI
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6, duration: 0.6 }}
              className="text-xl text-muted-foreground max-w-2xl mx-auto"
            >
              Your intelligent travel companion powered by advanced AI. Get personalized
              recommendations, detailed itineraries, and insider tips for unforgettable
              journeys.
            </motion.p>
          </div>
        </motion.div>

        {/* Enhanced feature showcase */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8, duration: 0.6 }}
          className="grid grid-cols-1 md:grid-cols-4 gap-4"
        >
          {[
            {
              icon: Plane,
              title: "Smart Flight Search",
              desc: "Find optimal routes and deals",
              color: "text-blue-500",
              bgGradient: "from-blue-500/10 to-sky-500/10",
            },
            {
              icon: MapPin,
              title: "Destination Intel",
              desc: "Discover hidden gems and locals' favorites",
              color: "text-green-500",
              bgGradient: "from-green-500/10 to-emerald-500/10",
            },
            {
              icon: Star,
              title: "Personalized AI",
              desc: "Learns your preferences and style",
              color: "text-yellow-500",
              bgGradient: "from-yellow-500/10 to-orange-500/10",
            },
            {
              icon: Zap,
              title: "Instant Planning",
              desc: "Complete itineraries in seconds",
              color: "text-purple-500",
              bgGradient: "from-purple-500/10 to-pink-500/10",
            },
          ].map(({ icon: Icon, title, desc, color, bgGradient }, index) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 20, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ delay: 1 + index * 0.1, duration: 0.5 }}
              whileHover={{
                y: -5,
                transition: { duration: 0.2 },
              }}
            >
              <Card
                className={cn(
                  "border-dashed hover:border-solid transition-all duration-300 hover:shadow-lg cursor-pointer",
                  "bg-gradient-to-br",
                  bgGradient
                )}
              >
                <CardContent className="p-6 text-center space-y-3">
                  <motion.div
                    whileHover={{ scale: 1.1, rotate: 5 }}
                    transition={{ duration: 0.2 }}
                  >
                    <Icon className={cn("w-10 h-10 mx-auto", color)} />
                  </motion.div>
                  <h3 className="font-semibold text-sm">{title}</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {desc}
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>

        {/* Advanced suggestion interface */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.2, duration: 0.6 }}
          className="space-y-8"
        >
          <div className="flex items-center justify-center gap-3">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{
                duration: 8,
                repeat: Number.POSITIVE_INFINITY,
                ease: "linear",
              }}
            >
              <Sparkles className="w-6 h-6 text-yellow-500" />
            </motion.div>
            <span className="text-lg font-medium text-foreground">
              Choose your adventure
            </span>
            <motion.div
              animate={{ rotate: -360 }}
              transition={{
                duration: 8,
                repeat: Number.POSITIVE_INFINITY,
                ease: "linear",
              }}
            >
              <Globe className="w-6 h-6 text-blue-500" />
            </motion.div>
          </div>

          <TooltipProvider delayDuration={300}>
            <div className="grid gap-8">
              {suggestionCategories.map((category, categoryIndex) => (
                <motion.div
                  key={category.title}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{
                    delay: 1.4 + categoryIndex * 0.2,
                    duration: 0.5,
                  }}
                  className="space-y-4"
                >
                  <div className="flex items-center justify-center gap-3">
                    <motion.div
                      whileHover={{ scale: 1.2 }}
                      transition={{ duration: 0.2 }}
                    >
                      <category.icon className={cn("w-5 h-5", category.color)} />
                    </motion.div>
                    <Badge
                      variant="secondary"
                      className="text-sm font-medium px-3 py-1"
                    >
                      {category.title}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {category.suggestions.map((suggestion, suggestionIndex) => (
                      <motion.div
                        key={suggestion.text}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{
                          delay: 1.6 + categoryIndex * 0.2 + suggestionIndex * 0.1,
                          duration: 0.4,
                        }}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                      >
                        <HoverCard>
                          <HoverCardTrigger asChild>
                            <Card
                              className={cn(
                                "cursor-pointer transition-all duration-300 hover:shadow-lg",
                                "bg-gradient-to-br",
                                category.gradient,
                                "border-2 border-transparent hover:border-primary/20"
                              )}
                            >
                              <CardHeader className="pb-3">
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <MessageSquare className="w-4 h-4 text-primary" />
                                    <Badge
                                      variant={
                                        suggestion.difficulty === "Easy"
                                          ? "secondary"
                                          : suggestion.difficulty === "Medium"
                                            ? "default"
                                            : "destructive"
                                      }
                                      className="text-xs"
                                    >
                                      {suggestion.difficulty}
                                    </Badge>
                                  </div>
                                  <motion.div
                                    whileHover={{ x: 5 }}
                                    transition={{ duration: 0.2 }}
                                  >
                                    <ArrowUp className="w-4 h-4 text-muted-foreground rotate-45" />
                                  </motion.div>
                                </div>
                              </CardHeader>
                              <CardContent className="pt-0">
                                <Button
                                  variant="ghost"
                                  className="w-full text-left h-auto p-0 justify-start"
                                  onClick={() => handleSuggestionClick(suggestion.text)}
                                >
                                  <span className="text-sm leading-relaxed font-medium">
                                    {suggestion.text}
                                  </span>
                                </Button>
                                <div className="flex flex-wrap gap-1 mt-3">
                                  {suggestion.tags.map((tag) => (
                                    <Badge
                                      key={tag}
                                      variant="outline"
                                      className="text-xs px-2 py-0.5"
                                    >
                                      {tag}
                                    </Badge>
                                  ))}
                                </div>
                              </CardContent>
                            </Card>
                          </HoverCardTrigger>
                          <HoverCardContent className="w-80">
                            <div className="space-y-3">
                              <div className="flex items-center gap-2">
                                <category.icon
                                  className={cn("w-4 h-4", category.color)}
                                />
                                <span className="font-medium">
                                  {category.title} Suggestion
                                </span>
                              </div>
                              <p className="text-sm text-muted-foreground">
                                This {suggestion.difficulty.toLowerCase()}-level query
                                will help you get {category.title.toLowerCase()}{" "}
                                recommendations tailored to your preferences.
                              </p>
                              <Separator />
                              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <Copy className="w-3 h-3" />
                                <span>Click to start this conversation</span>
                              </div>
                            </div>
                          </HoverCardContent>
                        </HoverCard>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              ))}
            </div>
          </TooltipProvider>
        </motion.div>

        {/* Enhanced call to action */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 2, duration: 0.6 }}
          className="pt-8 space-y-4"
        >
          <div className="flex items-center justify-center gap-4">
            <motion.div
              className="flex items-center gap-2 px-4 py-2 rounded-full bg-muted/50"
              whileHover={{ scale: 1.05 }}
              transition={{ duration: 0.2 }}
            >
              <Volume2 className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                Or speak your question naturally
              </span>
            </motion.div>
            <motion.div
              className="flex items-center gap-2 px-4 py-2 rounded-full bg-muted/50"
              whileHover={{ scale: 1.05 }}
              transition={{ duration: 0.2 }}
            >
              <Camera className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                Upload photos for context
              </span>
            </motion.div>
          </div>
          <p className="text-sm text-muted-foreground">
            Ready to explore? Type your travel dreams in the message box below
          </p>
        </motion.div>
      </div>
    </motion.div>
  );

  return (
    <ScrollArea
      className={cn("flex-1 relative", className)}
      ref={containerRef}
      onScrollCapture={handleScroll}
    >
      <div className="min-h-full relative">
        <AnimatePresence mode="wait">
          {messages.length === 0 ? (
            <motion.div
              key="empty-state"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <EmptyState />
            </motion.div>
          ) : (
            <motion.div
              key="messages-state"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              className="space-y-6 px-4 pt-4 pb-10"
            >
              <AnimatePresence mode="popLayout">
                {messages.map((message, index) => (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 20, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -20, scale: 0.95 }}
                    transition={{
                      duration: 0.4,
                      delay: index * 0.05,
                      ease: "easeOut",
                    }}
                    layout="position"
                    layoutId={`message-${message.id}`}
                  >
                    <MessageItem
                      message={message}
                      activeToolCalls={activeToolCalls}
                      toolResults={toolResults}
                      onRetryToolCall={onRetryToolCall}
                      onCancelToolCall={onCancelToolCall}
                    />
                  </motion.div>
                ))}
              </AnimatePresence>

              {/* Enhanced typing indicator */}
              <AnimatePresence>
                {sessionId && typingUsers.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 20, scale: 0.8 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -10, scale: 0.8 }}
                    transition={{ duration: 0.3, ease: "easeOut" }}
                    className="mx-4"
                  >
                    <Card className="bg-gradient-to-r from-blue-50/50 to-purple-50/50 dark:from-blue-950/20 dark:to-purple-950/20 border-dashed">
                      <CardContent className="p-4">
                        <TypingIndicator
                          typingUsers={typingUsers}
                          sessionId={sessionId}
                        />
                      </CardContent>
                    </Card>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Enhanced streaming indicator */}
              <AnimatePresence>
                {isStreaming && (
                  <motion.div
                    initial={{ opacity: 0, y: 20, scale: 0.8 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -10, scale: 0.8 }}
                    transition={{ duration: 0.4, ease: "easeOut" }}
                    className="mx-4"
                  >
                    <Card className="bg-gradient-to-r from-emerald-50/50 to-blue-50/50 dark:from-emerald-950/20 dark:to-blue-950/20 border border-primary/20">
                      <CardContent className="py-6">
                        <div className="flex items-center justify-center space-x-4">
                          <div className="relative">
                            <motion.div
                              animate={{ rotate: 360 }}
                              transition={{
                                duration: 2,
                                repeat: Number.POSITIVE_INFINITY,
                                ease: "linear",
                              }}
                            >
                              <Loader2 className="h-5 w-5 text-primary" />
                            </motion.div>
                            <motion.div
                              className="absolute inset-0"
                              animate={{ scale: [1, 1.2, 1] }}
                              transition={{
                                duration: 2,
                                repeat: Number.POSITIVE_INFINITY,
                                ease: "easeInOut",
                              }}
                            >
                              <div className="w-5 h-5 border-2 border-primary/20 rounded-full" />
                            </motion.div>
                          </div>

                          <div className="flex flex-col items-center space-y-1">
                            <motion.span
                              className="text-sm font-medium text-primary"
                              animate={{ opacity: [0.5, 1, 0.5] }}
                              transition={{
                                duration: 2,
                                repeat: Number.POSITIVE_INFINITY,
                                ease: "easeInOut",
                              }}
                            >
                              TripSage is crafting your perfect response...
                            </motion.span>
                            <div className="flex items-center space-x-1">
                              {[0, 1, 2].map((i) => (
                                <motion.div
                                  key={i}
                                  className="w-1.5 h-1.5 bg-primary/60 rounded-full"
                                  animate={{ scale: [1, 1.5, 1] }}
                                  transition={{
                                    duration: 1.5,
                                    repeat: Number.POSITIVE_INFINITY,
                                    delay: i * 0.2,
                                    ease: "easeInOut",
                                  }}
                                />
                              ))}
                            </div>
                          </div>

                          <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                            <Sparkles className="w-3 h-3" />
                            <span>AI at work</span>
                          </div>
                        </div>

                        {/* Progress indication */}
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: "100%" }}
                          transition={{ duration: 3, ease: "easeInOut" }}
                          className="mt-4"
                        >
                          <Progress value={85} className="h-1" />
                        </motion.div>
                      </CardContent>
                    </Card>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Scroll to bottom indicator */}
              <AnimatePresence>
                {userScrolledUp && messages.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 20 }}
                    transition={{ duration: 0.3 }}
                    className="fixed bottom-20 right-6 z-10"
                  >
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            size="sm"
                            variant="secondary"
                            className="rounded-full shadow-lg hover:shadow-xl transition-all duration-200"
                            onClick={() => {
                              bottomRef.current?.scrollIntoView({
                                behavior: "smooth",
                              });
                              setUserScrolledUp(false);
                            }}
                          >
                            <ArrowUp className="w-4 h-4" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Scroll to latest message</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </motion.div>
                )}
              </AnimatePresence>

              <div ref={bottomRef} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </ScrollArea>
  );
}
