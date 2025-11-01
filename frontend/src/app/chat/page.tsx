/**
 * @fileoverview Chat page integrating AI Elements primitives with AI SDK v6.
 * Renders a conversation and a prompt input wired to `/api/chat/stream`.
 */
"use client";

import { useCallback, useRef, useState } from "react";
import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import {
  Message,
  MessageAvatar,
  MessageContent,
} from "@/components/ai-elements/message";
import {
  PromptInput,
  PromptInputActionAddAttachments,
  PromptInputActionMenu,
  PromptInputActionMenuContent,
  PromptInputActionMenuItem,
  PromptInputActionMenuTrigger,
  PromptInputAttachment,
  PromptInputAttachments,
  PromptInputBody,
  PromptInputFooter,
  PromptInputHeader,
  type PromptInputMessage,
  PromptInputProvider,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
} from "@/components/ai-elements/prompt-input";

/**
 * Render a single message with support for text, tool usage, and simple metadata.
 */
function ChatMessageItem({
  role,
  id,
  parts,
}: {
  role: "user" | "assistant" | "system";
  id: string;
  parts: Array<any> | undefined;
}) {
  return (
    <Message from={role} data-testid={`msg-${id}`}>
      <MessageAvatar
        src={role === "user" ? "/avatar-user.png" : "/avatar-ai.png"}
        name={role === "user" ? "You" : "AI"}
      />
      <MessageContent>
        {Array.isArray(parts) && parts.length > 0 ? (
          parts.map((part, idx) => {
            switch (part?.type) {
              case "text":
                return (
                  <p key={`${id}-t-${idx}`} className="whitespace-pre-wrap">
                    {part.text}
                  </p>
                );
              case "tool-call":
              case "tool":
              case "tool-call-result":
                return (
                  <div
                    key={`${id}-tool-${idx}`}
                    className="my-2 rounded-md border bg-muted/30 p-3 text-xs"
                  >
                    <div className="mb-1 font-medium">Tool</div>
                    <pre className="overflow-x-auto whitespace-pre-wrap">
                      {JSON.stringify(part, null, 2)}
                    </pre>
                  </div>
                );
              case "reasoning":
                return (
                  <div
                    key={`${id}-r-${idx}`}
                    className="my-2 rounded-md border border-yellow-300/50 bg-yellow-50 p-3 text-xs text-yellow-900 dark:border-yellow-300/30 dark:bg-yellow-950 dark:text-yellow-200"
                  >
                    <div className="mb-1 font-medium">Reasoning</div>
                    <pre className="whitespace-pre-wrap">
                      {part.text ?? String(part)}
                    </pre>
                  </div>
                );
              default:
                return (
                  <pre key={`${id}-u-${idx}`} className="text-xs opacity-70">
                    {JSON.stringify(part)}
                  </pre>
                );
            }
          })
        ) : (
          <span className="opacity-70">(no content)</span>
        )}
      </MessageContent>
    </Message>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<
    Array<{ id: string; role: "user" | "assistant" | "system"; parts: any[] }>
  >([]);
  const abortRef = useRef<AbortController | null>(null);

  const handleSend = useCallback(async (text: string) => {
    const id =
      typeof crypto !== "undefined" && (crypto as any).randomUUID
        ? // eslint-disable-next-line @typescript-eslint/no-unsafe-call
          (crypto as any).randomUUID()
        : Math.random().toString(36).slice(2);
    const user = {
      id: `${id}-u`,
      role: "user" as const,
      parts: [{ type: "text", text }],
    };
    const assistant = {
      id: `${id}-a`,
      role: "assistant" as const,
      parts: [{ type: "text", text: "" }],
    };
    setMessages((prev) => prev.concat([user, assistant]));

    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    const payload = {
      messages: [
        {
          id: user.id,
          role: "user",
          content: [{ type: "text", text }],
        },
      ],
    };

    const res = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
      signal: ac.signal,
    });

    if (!res.ok || !res.body) return;

    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const delta = decoder.decode(value);
      setMessages((prev) => {
        const next = [...prev];
        const idx = next.findIndex((m) => m.id === assistant.id);
        if (idx !== -1) {
          const part = next[idx].parts[0];
          next[idx] = {
            ...next[idx],
            parts: [{ ...part, text: (part.text || "") + delta }],
          };
        }
        return next;
      });
    }
  }, []);

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      <Conversation className="flex-1">
        <ConversationContent>
          {messages.length === 0 ? (
            <ConversationEmptyState description="Start a conversation to see messages here." />
          ) : (
            messages.map((m) => (
              <ChatMessageItem
                key={m.id}
                id={m.id}
                role={m.role as any}
                parts={(m as any).parts}
              />
            ))
          )}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      <div className="border-t p-2">
        <PromptInputProvider>
          <PromptInput
            onSubmit={(msg: PromptInputMessage) => {
              const text = msg.text?.trim() ?? "";
              if (!text) return;
              void handleSend(text);
            }}
          >
            <PromptInputHeader>
              <PromptInputTools>
                <PromptInputActionMenu>
                  <PromptInputActionMenuTrigger aria-label="More actions" />
                  <PromptInputActionMenuContent>
                    <PromptInputActionAddAttachments />
                    <PromptInputActionMenuItem disabled>
                      Model settings (coming soon)
                    </PromptInputActionMenuItem>
                  </PromptInputActionMenuContent>
                </PromptInputActionMenu>
              </PromptInputTools>
            </PromptInputHeader>
            <PromptInputBody>
              <PromptInputTextarea
                placeholder="Ask TripSage AI anything about travel planning…"
                aria-label="Chat prompt"
              />
              <div className="flex flex-wrap gap-2 px-2 py-1">
                <PromptInputAttachments>
                  {(file) => <PromptInputAttachment data={file} />}
                </PromptInputAttachments>
              </div>
            </PromptInputBody>
            <PromptInputFooter>
              <div className="ml-auto">
                <PromptInputSubmit />
              </div>
            </PromptInputFooter>
          </PromptInput>
        </PromptInputProvider>
      </div>
    </div>
  );
}
