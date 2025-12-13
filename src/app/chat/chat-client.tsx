/**
 * @fileoverview Client chat shell using AI SDK v6 useChat hook for real streaming.
 */

"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { RefreshCwIcon, StopCircleIcon } from "lucide-react";
import type { ReactElement } from "react";
import { useState } from "react";
import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputHeader,
  PromptInputSubmit,
  PromptInputTextarea,
} from "@/components/ai-elements/prompt-input";
import { ChatMessageItem } from "@/components/chat/message-item";
import { Button } from "@/components/ui/button";

/**
 * Client-side chat container using AI SDK v6 useChat hook.
 * Connects to /api/chat/stream for real-time streaming responses.
 */
export function ChatClient(): ReactElement {
  const [input, setInput] = useState("");

  const { messages, sendMessage, status, error, stop, regenerate } = useChat({
    transport: new DefaultChatTransport({
      api: "/api/chat/stream",
    }),
  });

  const isStreaming = status === "streaming";
  const isSubmitting = status === "submitted";
  const isLoading = isStreaming || isSubmitting;
  const lastMessageId = messages.at(-1)?.id;

  const handleSubmit = async (text?: string) => {
    const messageText = text?.trim() || input.trim();
    if (!messageText || isLoading) return;

    try {
      await sendMessage({ text: messageText });
    } catch (err) {
      if (process.env.NODE_ENV === "development") {
        console.error("Failed to submit chat message:", err);
      }
    } finally {
      setInput("");
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      <Conversation className="flex-1">
        <ConversationContent>
          {messages.length === 0 ? (
            <ConversationEmptyState description="Start a conversation to see messages here." />
          ) : (
            messages.map((message) => (
              <ChatMessageItem
                key={message.id}
                message={message}
                isStreaming={
                  isStreaming &&
                  message.role === "assistant" &&
                  message.id === lastMessageId
                }
              />
            ))
          )}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      <div className="border-t p-2">
        <PromptInput onSubmit={({ text }) => handleSubmit(text)}>
          <PromptInputHeader />
          <PromptInputBody>
            <PromptInputTextarea
              placeholder="Ask TripSage AI anything about travel planning…"
              aria-label="Chat prompt"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
            />
          </PromptInputBody>
          <PromptInputFooter>
            <div className="flex items-center gap-2">
              {/* Streaming controls */}
              {isStreaming ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => stop()}
                  aria-label="Stop generation"
                >
                  <StopCircleIcon className="mr-1 size-4" />
                  Stop
                </Button>
              ) : null}

              {/* Regenerate button - only show when ready and there are messages */}
              {status === "ready" && messages.length > 0 ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => regenerate()}
                  aria-label="Regenerate response"
                >
                  <RefreshCwIcon className="mr-1 size-4" />
                  Regenerate
                </Button>
              ) : null}
            </div>

            <div className="ml-auto">
              <PromptInputSubmit status={isLoading ? "streaming" : undefined} />
            </div>
          </PromptInputFooter>
        </PromptInput>

        {/* Error display with retry */}
        {error ? (
          <div
            className="mt-2 flex items-center justify-between rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2"
            data-testid="chat-error"
          >
            <p className="text-sm text-destructive">
              {error.message || "An error occurred"}
            </p>
            <Button
              type="button"
              variant="link"
              size="sm"
              onClick={() => regenerate()}
              className="text-destructive"
            >
              Retry
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
