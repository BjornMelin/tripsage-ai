"use client";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { Paperclip, Send, Smile } from "lucide-react";
import { type KeyboardEvent, useCallback, useRef, useState } from "react";

export interface MessageInputProps {
  onSendMessage: (content: string) => Promise<void>;
  onStartTyping?: () => void;
  onStopTyping?: () => void;
  disabled?: boolean;
  placeholder?: string;
  maxLength?: number;
  className?: string;
}

export function MessageInput({
  onSendMessage,
  onStartTyping,
  onStopTyping,
  disabled = false,
  placeholder = "Type a message...",
  maxLength = 1000,
  className,
}: MessageInputProps) {
  const [content, setContent] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleSubmit = useCallback(async () => {
    if (!content.trim() || isSubmitting || disabled) {
      return;
    }

    const messageContent = content.trim();
    setContent("");
    setIsSubmitting(true);

    // Stop typing indicator since we're sending
    onStopTyping?.();

    try {
      await onSendMessage(messageContent);
    } catch (error) {
      // Restore content on error
      setContent(messageContent);
      console.error("Failed to send message:", error);
    } finally {
      setIsSubmitting(false);
      // Focus back to textarea
      textareaRef.current?.focus();
    }
  }, [content, isSubmitting, disabled, onSendMessage, onStopTyping]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter") {
        if (e.shiftKey) {
          // Allow new line with Shift+Enter
          return;
        } else {
          // Send message with Enter
          e.preventDefault();
          handleSubmit();
        }
      }
    },
    [handleSubmit]
  );

  const handleContentChange = useCallback(
    (value: string) => {
      setContent(value);

      // Handle typing indicators
      if (value.trim() && onStartTyping) {
        onStartTyping();

        // Clear existing timeout
        if (typingTimeoutRef.current) {
          clearTimeout(typingTimeoutRef.current);
        }

        // Stop typing after 3 seconds of inactivity
        typingTimeoutRef.current = setTimeout(() => {
          onStopTyping?.();
        }, 3000);
      } else if (!value.trim() && onStopTyping) {
        onStopTyping();
        if (typingTimeoutRef.current) {
          clearTimeout(typingTimeoutRef.current);
          typingTimeoutRef.current = null;
        }
      }
    },
    [onStartTyping, onStopTyping]
  );

  // Auto-resize textarea
  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, []);

  return (
    <div className={cn("border-t bg-background p-4", className)}>
      <div className="flex items-end gap-2">
        {/* Attachment button */}
        <Button
          variant="ghost"
          size="icon"
          className="shrink-0 mb-1"
          disabled={disabled}
        >
          <Paperclip className="h-4 w-4" />
          <span className="sr-only">Attach file</span>
        </Button>

        {/* Message input */}
        <div className="flex-1 relative">
          <Textarea
            ref={textareaRef}
            value={content}
            onChange={(e) => {
              handleContentChange(e.target.value);
              adjustTextareaHeight();
            }}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled || isSubmitting}
            maxLength={maxLength}
            className={cn(
              "min-h-[44px] max-h-[120px] resize-none pr-12",
              "placeholder:text-muted-foreground",
              "focus-visible:ring-1"
            )}
            style={{ height: "44px" }}
          />

          {/* Character count */}
          {content.length > maxLength * 0.8 && (
            <div className="absolute bottom-2 left-3 text-xs text-muted-foreground">
              {content.length}/{maxLength}
            </div>
          )}
        </div>

        {/* Emoji button */}
        <Button
          variant="ghost"
          size="icon"
          className="shrink-0 mb-1"
          disabled={disabled}
        >
          <Smile className="h-4 w-4" />
          <span className="sr-only">Add emoji</span>
        </Button>

        {/* Send button */}
        <Button
          onClick={handleSubmit}
          disabled={!content.trim() || disabled || isSubmitting}
          size="icon"
          className="shrink-0 mb-1"
        >
          <Send className="h-4 w-4" />
          <span className="sr-only">Send message</span>
        </Button>
      </div>

      {/* Help text */}
      <div className="mt-2 text-xs text-muted-foreground">
        Press <kbd className="px-1 py-0.5 text-xs bg-muted rounded">Enter</kbd> to send,{" "}
        <kbd className="px-1 py-0.5 text-xs bg-muted rounded">Shift</kbd> +{" "}
        <kbd className="px-1 py-0.5 text-xs bg-muted rounded">Enter</kbd> for new line
      </div>
    </div>
  );
}
