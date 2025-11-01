"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  isStreaming?: boolean;
}

interface ChatInterfaceProps {
  className?: string;
  placeholder?: string;
  disabled?: boolean;
  sessionId?: string;
}

// Sample messages for demo purposes
const SAMPLE_MESSAGES: Message[] = [
  {
    id: "1",
    role: "assistant",
    content:
      "Hello! I'm your TripSage AI assistant. I can help you plan trips, find flights, book accommodations, and answer travel questions. What can I help you with today?",
    timestamp: new Date(Date.now() - 60000).toISOString(),
  },
  {
    id: "2",
    role: "user",
    content:
      "I'm looking for flights from New York to Paris for next month. Can you help?",
    timestamp: new Date(Date.now() - 30000).toISOString(),
  },
  {
    id: "3",
    role: "assistant",
    content:
      "I'd be happy to help you find flights from New York to Paris! To provide you with the best options, I'll need a few more details:\n\n• What are your preferred travel dates?\n• How many passengers?\n• Do you have a preference for cabin class (Economy, Business, etc.)?\n• Any preferred airlines or specific requirements?\n\nOnce I have these details, I can search for the best flight options for you.",
    timestamp: new Date(Date.now() - 15000).toISOString(),
  },
];

function MessageBubble({
  message,
  className,
}: {
  message: Message;
  className?: string;
}) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  return (
    <div
      className={cn("flex w-full", isUser ? "justify-end" : "justify-start", className)}
    >
      <div
        className={cn(
          "relative max-w-[80%] lg:max-w-[70%] rounded-lg px-4 py-3 text-sm",
          isUser
            ? "bg-primary text-primary-foreground"
            : isSystem
              ? "bg-muted text-muted-foreground border"
              : "bg-muted text-foreground border",
          message.isStreaming && "animate-pulse"
        )}
      >
        <div className="whitespace-pre-wrap wrap-break-word">{message.content}</div>
        <div
          className={cn(
            "text-xs mt-1 opacity-60",
            isUser ? "text-primary-foreground/70" : "text-muted-foreground"
          )}
        >
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>
    </div>
  );
}

function MessageInput({
  onSendMessage,
  disabled,
  placeholder = "Type your message...",
}: {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSendMessage(input.trim());
      setInput("");
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  return (
    <form onSubmit={handleSubmit} className="flex gap-3 p-4 border-t bg-background">
      <div className="flex-1 relative">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className={cn(
            "w-full resize-none border rounded-lg px-4 py-3 text-sm",
            "focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            "min-h-[44px] max-h-32 overflow-y-auto"
          )}
        />
      </div>
      <button
        type="submit"
        disabled={!input.trim() || disabled}
        className={cn(
          "shrink-0 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
          "bg-primary text-primary-foreground hover:bg-primary/90",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          "h-[44px] flex items-center justify-center"
        )}
      >
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          role="img"
          aria-label="Send message"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
          />
        </svg>
      </button>
    </form>
  );
}

export function ChatInterface({
  className,
  placeholder,
  disabled = false,
  sessionId: _sessionId,
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>(SAMPLE_MESSAGES);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages are added
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = async (content: string) => {
    if (disabled || isLoading) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Simulate AI response
    setTimeout(
      () => {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content:
            "I understand you're looking for help with that. Let me process your request and provide you with the best assistance possible. This is a placeholder response while the actual AI integration is being implemented.",
          timestamp: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setIsLoading(false);
      },
      1000 + Math.random() * 2000
    ); // Random delay to simulate real response
  };

  return (
    <div className={cn("flex flex-col h-full bg-background", className)}>
      {/* Chat Header */}
      <div className="shrink-0 p-4 border-b">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">AI Assistant</h2>
            <p className="text-sm text-muted-foreground">
              Ask me anything about travel planning
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div
              className={cn(
                "w-2 h-2 rounded-full",
                isLoading ? "bg-yellow-500" : "bg-green-500"
              )}
            />
            <span className="text-xs text-muted-foreground">
              {isLoading ? "Thinking..." : "Online"}
            </span>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-muted border rounded-lg px-4 py-3 text-sm">
              <div className="flex items-center gap-2">
                <div className="flex space-x-1">
                  <div className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce [animation-delay:-0.3s]" />
                  <div className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce [animation-delay:-0.15s]" />
                  <div className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce" />
                </div>
                <span className="text-muted-foreground">AI is typing...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Message Input */}
      <MessageInput
        onSendMessage={handleSendMessage}
        disabled={disabled || isLoading}
        placeholder={placeholder}
      />
    </div>
  );
}
