"use client";

/**
 * @fileoverview Client chat shell rendering messages and invoking the server action.
 */

import type { UIMessage } from "ai";
import type { ReactElement } from "react";
import { useCallback, useState } from "react";
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
import { submitChatMessage } from "./ai";

/**
 * Client-side chat container that renders history and invokes the server action.
 */
export function ChatClient(): ReactElement {
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = useCallback(
    async (text: string) => {
      if (pending) return;
      if (!text.trim()) return;
      setPending(true);
      setError(null);

      try {
        const result = await submitChatMessage({ messages, text });
        setMessages((prev) => [...prev, result.userMessage, result.assistantMessage]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to send message.");
      } finally {
        setPending(false);
      }
    },
    [messages, pending]
  );

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      <Conversation className="flex-1">
        <ConversationContent>
          {messages.length === 0 ? (
            <ConversationEmptyState description="Start a conversation to see messages here." />
          ) : (
            messages.map((message) => (
              <ChatMessageItem key={message.id} message={message} />
            ))
          )}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      <div className="border-t p-2">
        <PromptInput onSubmit={({ text }) => handleSend(text ?? "")}>
          <PromptInputHeader />
          <PromptInputBody>
            <PromptInputTextarea
              placeholder="Ask TripSage AI anything about travel planning…"
              aria-label="Chat prompt"
              disabled={pending}
            />
          </PromptInputBody>
          <PromptInputFooter>
            <div className="ml-auto">
              <PromptInputSubmit status={pending ? "streaming" : undefined} />
            </div>
            {error ? (
              <p className="mt-2 text-sm text-destructive" data-testid="chat-error">
                {error}
              </p>
            ) : null}
          </PromptInputFooter>
        </PromptInput>
      </div>
    </div>
  );
}
