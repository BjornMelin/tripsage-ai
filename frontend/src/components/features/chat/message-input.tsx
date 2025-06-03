"use client";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { uploadAttachments } from "@/lib/api/chat-api";
import { Loader2, Mic, Paperclip, SendHorizontal, StopCircle } from "lucide-react";
import type React from "react";
import { FormEvent, useCallback, useRef, useState } from "react";

interface MessageInputProps {
  disabled?: boolean;
  placeholder?: string;
  showAttachmentButton?: boolean;
  showVoiceButton?: boolean;
  className?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onSend?: (message: string, attachments: string[]) => void;
  onCancel?: () => void;
  isStreaming?: boolean;
}

export function MessageInput({
  disabled,
  placeholder = "Type a message...",
  showAttachmentButton = true,
  showVoiceButton = true,
  className,
  value = "",
  onChange,
  onSend,
  onCancel,
  isStreaming = false,
}: MessageInputProps) {
  // Use local state if no controlled value is provided
  const [localInput, setLocalInput] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [attachments, setAttachments] = useState<File[]>([]);
  const [attachmentUrls, setAttachmentUrls] = useState<string[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Determine if using controlled or uncontrolled input
  const isControlled = onChange !== undefined;
  const inputValue = isControlled ? value : localInput;

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (isControlled) {
      onChange(e);
    } else {
      setLocalInput(e.target.value);
    }
  };

  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim() && attachments.length === 0) return;

    // If streaming and onCancel is provided, cancel the stream
    if (isStreaming && onCancel) {
      onCancel();
      return;
    }

    try {
      // Handle file uploads if needed
      let urls: string[] = [...attachmentUrls];

      if (attachments.length > 0) {
        setIsUploading(true);
        const result = await uploadAttachments(attachments);
        urls = [...urls, ...result.urls];
        setIsUploading(false);
      }

      // Send the message
      if (onSend) {
        onSend(inputValue.trim(), urls);
      }

      // Reset local state
      if (!isControlled) {
        setLocalInput("");
      }
      setAttachments([]);
      setAttachmentUrls([]);

      // Focus the textarea again
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    } catch (error) {
      console.error("Error handling message send:", error);
      setIsUploading(false);
    }
  }, [
    inputValue,
    attachments,
    attachmentUrls,
    isControlled,
    isStreaming,
    onSend,
    onCancel,
  ]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Send message on Enter (but not with Shift+Enter)
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleAttachmentClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setAttachments(Array.from(e.target.files));
    }
  };

  const handleRemoveAttachment = (index: number) => {
    setAttachments(attachments.filter((_, i) => i !== index));
  };

  const handleRemoveAttachmentUrl = (index: number) => {
    setAttachmentUrls(attachmentUrls.filter((_, i) => i !== index));
  };

  return (
    <div className="border-t p-4 bg-background">
      {/* Attachments preview */}
      {(attachments.length > 0 || attachmentUrls.length > 0) && (
        <div className="flex flex-wrap gap-2 mb-2">
          {/* Local file attachments */}
          {attachments.map((file, index) => (
            <div
              key={`file-${index}`}
              className="flex items-center gap-1 bg-secondary/50 text-secondary-foreground rounded-full pl-2 pr-1 py-1 text-xs"
            >
              <span className="truncate max-w-[100px]">{file.name}</span>
              <Button
                variant="ghost"
                size="icon"
                className="h-4 w-4 rounded-full"
                onClick={() => handleRemoveAttachment(index)}
              >
                ×
              </Button>
            </div>
          ))}

          {/* Remote attachment URLs */}
          {attachmentUrls.map((url, index) => (
            <div
              key={`url-${index}`}
              className="flex items-center gap-1 bg-secondary text-secondary-foreground rounded-full pl-2 pr-1 py-1 text-xs"
            >
              <span className="truncate max-w-[100px]">
                {url.split("/").pop() || "Attachment"}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-4 w-4 rounded-full"
                onClick={() => handleRemoveAttachmentUrl(index)}
              >
                ×
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Input area */}
      <div className="relative">
        <Textarea
          ref={textareaRef}
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || isUploading}
          className="min-h-[60px] resize-none pr-20 py-4"
          rows={1}
        />

        <div className="absolute right-2 bottom-2 flex items-center gap-2">
          {/* File attachment button */}
          {showAttachmentButton && (
            <>
              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                onChange={handleFileChange}
                multiple
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8 rounded-full"
                onClick={handleAttachmentClick}
                disabled={disabled || isStreaming || isUploading}
              >
                <Paperclip className="h-4 w-4" />
              </Button>
            </>
          )}

          {/* Voice input button (placeholder for future implementation) */}
          {showVoiceButton && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-8 rounded-full"
              disabled={true} // Disabled until implemented
            >
              <Mic className="h-4 w-4" />
            </Button>
          )}

          {/* Send button */}
          <Button
            type="button"
            variant={isStreaming ? "destructive" : "default"}
            size="icon"
            className="h-8 w-8 rounded-full"
            onClick={handleSendMessage}
            disabled={
              disabled ||
              isUploading ||
              (!inputValue.trim() &&
                attachments.length === 0 &&
                attachmentUrls.length === 0 &&
                !isStreaming)
            }
          >
            {isUploading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : isStreaming ? (
              <StopCircle className="h-4 w-4" />
            ) : (
              <SendHorizontal className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
