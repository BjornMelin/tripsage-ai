"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  Code2,
  Copy,
  ExternalLink,
  FileText,
  Loader2,
  Shield,
  Sparkles,
  Zap,
} from "lucide-react";
import { useCallback, useMemo, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark, oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { Message } from "@/types/chat";

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

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
  isRealtime?: boolean;
  theme?: "light" | "dark";
}

export function MessageBubble({
  message,
  isStreaming = false,
  isRealtime = false,
  theme = "dark",
}: MessageBubbleProps) {
  const contentRef = useRef<HTMLDivElement>(null);

  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";
  const isSystem = message.role === "system";
  const isTool = false; // 'tool' role not supported in current Message type

  // role-based styling configuration
  const bubbleConfig = useMemo(() => {
    if (isUser) {
      return {
        className: cn(
          "bg-linear-to-br from-primary to-primary/90",
          "text-primary-foreground shadow-lg",
          "border border-primary/20"
        ),
        icon: null,
        iconColor: "",
        accentColor: "blue",
      };
    }

    if (isAssistant) {
      return {
        className: cn(
          "bg-linear-to-br from-card to-card/95",
          "border border-muted shadow-sm",
          "hover:shadow-md transition-shadow duration-300"
        ),
        icon: Sparkles,
        iconColor: "text-emerald-500",
        accentColor: "emerald",
      };
    }

    if (isSystem) {
      return {
        className: cn(
          "bg-linear-to-br from-yellow-500/10 to-orange-500/5",
          "border border-yellow-500/30 shadow-sm"
        ),
        icon: Shield,
        iconColor: "text-yellow-600 dark:text-yellow-400",
        accentColor: "yellow",
      };
    }

    if (isTool) {
      return {
        className: cn(
          "bg-linear-to-br from-purple-500/10 to-pink-500/5",
          "border border-purple-500/30 shadow-sm"
        ),
        icon: Activity,
        iconColor: "text-purple-600 dark:text-purple-400",
        accentColor: "purple",
      };
    }

    return {
      className: "bg-muted border",
      icon: FileText,
      iconColor: "text-muted-foreground",
      accentColor: "gray",
    };
  }, [isUser, isAssistant, isSystem, isTool]);

  // Handle copy content
  const handleCopyContent = useCallback(() => {
    const text = partsToText((message as any).parts) ?? message.content;
    if (text) navigator.clipboard.writeText(text);
  }, [message.content, message]);

  // markdown components with syntax highlighting
  const markdownComponents = useMemo(
    () => ({
      // code blocks with syntax highlighting
      code: ({ node, inline, className, children, ...props }: any) => {
        const match = /language-(\w+)/.exec(className || "");
        const language = match ? match[1] : "";

        if (!inline && language) {
          return (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3 }}
              className="relative group"
            >
              <div className="flex items-center justify-between bg-muted/50 px-4 py-2 rounded-t-lg border-b">
                <div className="flex items-center gap-2">
                  <Code2 className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm font-medium text-muted-foreground capitalize">
                    {language}
                  </span>
                </div>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={() => navigator.clipboard.writeText(String(children))}
                      >
                        <Copy className="w-3 h-3" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Copy code</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
              <SyntaxHighlighter
                style={theme === "dark" ? oneDark : oneLight}
                language={language}
                PreTag="div"
                className="rounded-t-none mt-0! !bg-background"
                showLineNumbers
                wrapLines
                {...props}
              >
                {String(children).replace(/\n$/, "")}
              </SyntaxHighlighter>
            </motion.div>
          );
        }

        // Inline code
        return (
          <motion.code
            initial={{ backgroundColor: "rgba(0,0,0,0)" }}
            animate={{ backgroundColor: "rgba(0,0,0,0.05)" }}
            transition={{ duration: 0.2 }}
            className={cn(
              "bg-muted/80 px-1.5 py-0.5 rounded text-sm font-mono",
              "border border-muted/50",
              className
            )}
            {...props}
          >
            {children}
          </motion.code>
        );
      },

      // pre blocks
      pre: ({ node, children, ...props }: any) => (
        <motion.pre
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className={cn(
            "bg-muted/50 p-4 rounded-lg overflow-x-auto border",
            "shadow-sm hover:shadow-md transition-shadow duration-300"
          )}
          {...props}
        >
          {children}
        </motion.pre>
      ),

      // links with external link indicator
      a: ({ node, href, children, ...props }: any) => (
        <motion.a
          whileHover={{ scale: 1.02 }}
          transition={{ duration: 0.1 }}
          className={cn(
            "text-primary underline underline-offset-2",
            "hover:text-primary/80 transition-colors duration-200",
            "inline-flex items-center gap-1"
          )}
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          {...props}
        >
          {children}
          <ExternalLink className="w-3 h-3 inline" />
        </motion.a>
      ),

      // headings
      h1: ({ children, ...props }: any) => (
        <motion.h1
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }}
          className="text-2xl font-bold mb-4 pb-2 border-b"
          {...props}
        >
          {children}
        </motion.h1>
      ),
      h2: ({ children, ...props }: any) => (
        <motion.h2
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }}
          className="text-xl font-semibold mb-3 pb-1 border-b border-muted/30"
          {...props}
        >
          {children}
        </motion.h2>
      ),
      h3: ({ children, ...props }: any) => (
        <motion.h3
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }}
          className="text-lg font-semibold mb-2"
          {...props}
        >
          {children}
        </motion.h3>
      ),

      // lists
      ul: ({ children, ...props }: any) => (
        <motion.ul
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3, staggerChildren: 0.1 }}
          className="list-disc list-inside space-y-1 mb-4"
          {...props}
        >
          {children}
        </motion.ul>
      ),
      ol: ({ children, ...props }: any) => (
        <motion.ol
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3, staggerChildren: 0.1 }}
          className="list-decimal list-inside space-y-1 mb-4"
          {...props}
        >
          {children}
        </motion.ol>
      ),
      li: ({ children, ...props }: any) => (
        <motion.li
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.2 }}
          className="mb-1"
          {...props}
        >
          {children}
        </motion.li>
      ),

      // blockquotes
      blockquote: ({ children, ...props }: any) => (
        <motion.blockquote
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }}
          className={cn(
            "border-l-4 border-primary/30 pl-4 py-2 my-4",
            "bg-muted/30 rounded-r-lg italic text-muted-foreground"
          )}
          {...props}
        >
          {children}
        </motion.blockquote>
      ),

      // tables
      table: ({ children, ...props }: any) => (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
          className="overflow-x-auto mb-4"
        >
          <table
            className="w-full border-collapse border border-muted rounded-lg"
            {...props}
          >
            {children}
          </table>
        </motion.div>
      ),
      th: ({ children, ...props }: any) => (
        <th
          className="border border-muted bg-muted/50 px-4 py-2 text-left font-semibold"
          {...props}
        >
          {children}
        </th>
      ),
      td: ({ children, ...props }: any) => (
        <td className="border border-muted px-4 py-2" {...props}>
          {children}
        </td>
      ),
    }),
    [theme]
  );

  // Empty fallback content with animation
  const emptyContent = isUser ? "..." : "_";

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95, y: -10 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      whileHover={{ scale: 1.01 }}
      className={cn(
        "relative py-3 px-4 rounded-xl group",
        "transition-all duration-300",
        bubbleConfig.className,
        isStreaming && "animate-pulse",
        isRealtime && !isStreaming && "ring-2 ring-emerald-500/20 shadow-emerald-500/10"
      )}
    >
      {/* Streaming indicator */}
      <AnimatePresence>
        {isStreaming && (
          <motion.div
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.5 }}
            transition={{ duration: 0.2 }}
            className="absolute -right-3 -top-3 z-10"
          >
            <div className="bg-emerald-500 rounded-full p-1.5 shadow-lg">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{
                  duration: 1,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "linear",
                }}
              >
                <Loader2 className="h-3 w-3 text-white" />
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Role indicator for non-user messages */}
      {!isUser && bubbleConfig.icon && (
        <motion.div
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1, duration: 0.2 }}
          className="absolute -left-2 -top-2"
        >
          <div
            className={cn(
              "w-6 h-6 rounded-full border-2 border-background",
              "flex items-center justify-center shadow-sm",
              isAssistant && "bg-emerald-500",
              isSystem && "bg-yellow-500",
              isTool && "bg-purple-500"
            )}
          >
            <bubbleConfig.icon className="w-3 h-3 text-white" />
          </div>
        </motion.div>
      )}

      {/* Content */}
      <motion.div
        ref={contentRef}
        className={cn(
          "prose prose-sm max-w-none wrap-break-word",
          isUser ? "prose-invert" : "dark:prose-invert",
          // Customize prose colors based on role
          !isUser && "prose-headings:text-foreground prose-p:text-foreground",
          !isUser && "prose-strong:text-foreground prose-em:text-muted-foreground",
          !isUser && "prose-code:text-foreground"
        )}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1, duration: 0.4 }}
      >
        <ReactMarkdown components={markdownComponents}>
          {message.content || emptyContent}
        </ReactMarkdown>
      </motion.div>

      {/* action buttons for hover state */}
      <motion.div
        className={cn(
          "absolute top-2 right-2 flex items-center gap-1",
          "opacity-0 group-hover:opacity-100 transition-opacity duration-200"
        )}
        initial={{ opacity: 0, x: 10 }}
        animate={{ opacity: 0, x: 0 }}
      >
        {message.content && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  size="sm"
                  variant="ghost"
                  className={cn(
                    "h-6 w-6 p-0 hover:bg-background/20",
                    isUser && "hover:bg-white/20"
                  )}
                  onClick={handleCopyContent}
                >
                  <Copy className="w-3 h-3" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Copy message</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </motion.div>

      {/* Realtime indicator */}
      <AnimatePresence>
        {isRealtime && !isStreaming && (
          <motion.div
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.5 }}
            transition={{ duration: 0.2 }}
            className="absolute -bottom-1 -right-1"
          >
            <div className="bg-emerald-500 rounded-full p-1">
              <motion.div
                animate={{ scale: [1, 1.2, 1] }}
                transition={{
                  duration: 2,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "easeInOut",
                }}
              >
                <Zap className="w-2 h-2 text-white" />
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
