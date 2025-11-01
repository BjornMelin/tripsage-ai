/**
 * @fileoverview Chat page integrating AI Elements primitives with AI SDK v6.
 * Renders a conversation and a prompt input wired to `/api/chat/stream`.
 */
"use client";

import { useRef, useState } from "react";
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
              const parts: any[] = [];
              const text = (msg.text || "").trim();
              if (text) parts.push({ type: "text", text });
              if (Array.isArray(msg.files)) {
                for (const f of msg.files) {
                  parts.push({
                    type: "file",
                    url: f.url,
                    media_type: f.mediaType,
                    name: f.filename,
                  });
                }
              }
              if (parts.length === 0) return;

              const userId = Math.random().toString(36).slice(2);
              setMessages((prev: any[]) =>
                prev.concat([{ id: userId, role: "user", parts }])
              );

              abortRef.current?.abort();
              const ac = new AbortController();
              abortRef.current = ac;

              const payload = { messages: [{ id: userId, role: "user", parts }] };

              void (async () => {
                const res = await fetch("/api/chat/stream", {
                  method: "POST",
                  headers: { "content-type": "application/json" },
                  body: JSON.stringify(payload),
                  signal: ac.signal,
                });
                if (!res.ok || !res.body) return;
                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                let buffer = "";
                while (true) {
                  const { done, value } = await reader.read();
                  if (done) break;
                  buffer += decoder.decode(value, { stream: true });
                  let idx;
                  while ((idx = buffer.indexOf("\n\n")) !== -1) {
                    const event = buffer.slice(0, idx).trim();
                    buffer = buffer.slice(idx + 2);
                    if (event.startsWith("data:")) {
                      const dataStr = event.slice(5).trim();
                      if (dataStr === "[DONE]") break;
                      try {
                        const msgObj = JSON.parse(dataStr) as any;
                        if (msgObj?.role) {
                          setMessages((prev: any[]) =>
                            prev.concat([
                              {
                                id: msgObj.id || Math.random().toString(36).slice(2),
                                role: msgObj.role,
                                parts: msgObj.parts || [],
                              },
                            ])
                          );
                        }
                      } catch {
                        // ignore parse errors for non-JSON events
                      }
                    }
                  }
                }
              })();
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
