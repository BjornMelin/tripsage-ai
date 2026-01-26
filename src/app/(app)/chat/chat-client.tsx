/**
 * @fileoverview Client chat shell using AI SDK v6 useChat hook for real streaming.
 */

"use client";

import { useChat } from "@ai-sdk/react";
import {
  type AiStreamStatus,
  type ChatMessageMetadata,
  chatDataPartSchemas,
  chatMessageMetadataSchema,
} from "@schemas/ai";
import { attachmentCreateSignedUploadResponseSchema } from "@schemas/attachments";
import type { UIMessage } from "ai";
import { DefaultChatTransport } from "ai";
import { PaperclipIcon, RefreshCwIcon, StopCircleIcon, XIcon } from "lucide-react";
import type { ReactElement } from "react";
import { useEffect, useId, useRef, useState } from "react";
import { z } from "zod";
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
import { secureId } from "@/lib/security/random";
import { getBrowserClient } from "@/lib/supabase";

const STORAGE_BUCKET = "attachments";

const createSessionResponseSchema = z.strictObject({
  id: z.string().trim().min(1),
});

type ChatUiDataParts = {
  status: AiStreamStatus;
};

type ChatUiMessage = UIMessage<ChatMessageMetadata, ChatUiDataParts>;

type PendingAttachment = { file: File; id: string };

const CHAT_ERROR_FALLBACK = "An error occurred";
const CHAT_ERROR_REASON_MAP = new Map<string, string>([
  [
    "provider_unavailable",
    "AI provider is not configured yet. Add an API key in settings to enable chat.",
  ],
  [
    "rate_limit_unavailable",
    "Rate limiting is temporarily unavailable. Please try again shortly.",
  ],
]);

const chatErrorPayloadSchema = z.looseObject({
  error: z.string().optional(),
  reason: z.string().optional(),
});

function resolveChatErrorMessage(error?: Error): string {
  if (!error?.message) return CHAT_ERROR_FALLBACK;

  try {
    const parsed = chatErrorPayloadSchema.safeParse(JSON.parse(error.message));
    if (!parsed.success) return error.message || CHAT_ERROR_FALLBACK;
    if (parsed.data.error) {
      const mappedReason = CHAT_ERROR_REASON_MAP.get(parsed.data.error);
      if (mappedReason) return mappedReason;
    }
    if (parsed.data.reason?.trim()) {
      return parsed.data.reason;
    }
  } catch {
    // ignore JSON parse failures
  }

  return error.message || CHAT_ERROR_FALLBACK;
}

/**
 * Client-side chat container using AI SDK v6 useChat hook.
 * Connects to /api/chat for real-time UI message streaming responses.
 */
export function ChatClient(): ReactElement {
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [files, setFiles] = useState<PendingAttachment[]>([]);
  const [attachmentError, setAttachmentError] = useState<string | null>(null);
  const [streamStatus, setStreamStatus] = useState<AiStreamStatus | null>(null);
  const fileInputId = useId();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const pendingRequestRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      pendingRequestRef.current?.abort();
    };
  }, []);

  const { messages, sendMessage, status, error, stop, regenerate } =
    useChat<ChatUiMessage>({
      dataPartSchemas: chatDataPartSchemas,
      messageMetadataSchema: chatMessageMetadataSchema,
      onData: (dataPart) => {
        if (dataPart.type === "data-status") {
          setStreamStatus(dataPart.data);
        }
      },
      onFinish: ({ message }) => {
        const maybeSessionId = message.metadata?.sessionId;
        if (typeof maybeSessionId === "string" && maybeSessionId.trim().length > 0) {
          setSessionId(maybeSessionId);
        }
      },
      transport: new DefaultChatTransport({
        api: "/api/chat",
        prepareSendMessagesRequest: ({ body, id, messageId, messages, trigger }) => {
          const sessionId =
            body && typeof body === "object" && "sessionId" in body
              ? body.sessionId
              : undefined;

          const requestBody: Record<string, unknown> = { id, trigger };
          if (typeof sessionId === "string" && sessionId.trim().length > 0) {
            requestBody.sessionId = sessionId.trim();
          }
          if (typeof messageId === "string" && messageId.trim().length > 0) {
            requestBody.messageId = messageId.trim();
          }

          if (trigger === "submit-message") {
            const last = messages.at(-1);
            if (last) {
              requestBody.message = last;
            }
          }

          return { body: requestBody };
        },
      }),
    });

  useEffect(() => {
    if (status === "submitted" || status === "ready" || status === "error") {
      setStreamStatus(null);
    }
  }, [status]);

  const isStreaming = status === "streaming";
  const isSubmitting = status === "submitted";
  const isLoading = isStreaming || isSubmitting;
  const submitStatus =
    status === "error" ? "error" : isLoading ? "submitted" : undefined;
  const lastMessageId = messages.at(-1)?.id;

  const ensureSessionId = async (signal?: AbortSignal): Promise<string | null> => {
    if (sessionId) return sessionId;
    if (signal?.aborted) return null;

    try {
      const res = await fetch("/api/chat/sessions", {
        body: JSON.stringify({}),
        headers: { "content-type": "application/json" },
        method: "POST",
        signal,
      });

      if (signal?.aborted) return null;

      if (!res.ok) {
        return null;
      }

      const json = await res.json();
      const parsed = createSessionResponseSchema.safeParse(json);
      if (!parsed.success) return null;

      if (signal?.aborted) return null;
      setSessionId(parsed.data.id);
      return parsed.data.id;
    } catch (err) {
      const isAbort =
        (err instanceof DOMException && err.name === "AbortError") ||
        (err instanceof Error && err.name === "AbortError");
      if (isAbort) return null;

      if (process.env.NODE_ENV !== "production") {
        console.error("Failed to create chat session:", err);
      }
      return null;
    }
  };

  const uploadAttachments = async (
    chatId: string,
    signal?: AbortSignal
  ): Promise<boolean> => {
    if (files.length === 0) return true;
    const aborted = () => signal?.aborted === true;
    if (aborted()) return false;

    const supabase = getBrowserClient();
    if (!supabase) {
      if (!aborted()) {
        setAttachmentError("Supabase client not available");
      }
      return false;
    }

    const payload = {
      chatId,
      files: files.map(({ file }) => ({
        mimeType: file.type,
        originalName: file.name,
        size: file.size,
      })),
    };

    try {
      const res = await fetch("/api/chat/attachments", {
        body: JSON.stringify(payload),
        headers: { "content-type": "application/json" },
        method: "POST",
        signal,
      });

      if (aborted()) return false;

      if (!res.ok) {
        if (!aborted()) {
          setAttachmentError("Failed to prepare attachment uploads");
        }
        return false;
      }

      const json = await res.json();
      const parsed = attachmentCreateSignedUploadResponseSchema.safeParse(json);
      if (!parsed.success) {
        if (!aborted()) {
          setAttachmentError("Invalid attachment upload response");
        }
        return false;
      }

      if (parsed.data.uploads.length !== files.length) {
        if (!aborted()) {
          setAttachmentError("Attachment upload mismatch");
        }
        return false;
      }

      const results = await Promise.allSettled(
        parsed.data.uploads.map(async (upload, index) => {
          if (aborted()) {
            throw new DOMException("Aborted", "AbortError");
          }
          const entry = files[index];
          const file = entry?.file;
          if (!file) {
            throw new Error("Missing attachment file");
          }

          const { error: uploadError } = await supabase.storage
            .from(STORAGE_BUCKET)
            .uploadToSignedUrl(upload.path, upload.token, file, {
              contentType: upload.mimeType,
            });

          if (uploadError) {
            throw new Error(uploadError.message);
          }
        })
      );

      if (aborted()) return false;

      const hasFailures = results.some((result) => result.status === "rejected");
      if (hasFailures) {
        if (!aborted()) {
          setAttachmentError("Failed to upload attachment");
        }
        return false;
      }

      setFiles([]);
      setAttachmentError(null);
      return true;
    } catch (err) {
      const isAbort =
        aborted() ||
        (err instanceof DOMException && err.name === "AbortError") ||
        (err instanceof Error && err.name === "AbortError");

      if (isAbort) {
        return false;
      }

      setAttachmentError("Failed to upload attachment");
      return false;
    }
  };

  const handleSubmit = async (text?: string) => {
    const messageText = text?.trim() || input.trim();
    if (!messageText || isLoading) return;

    const controller = new AbortController();
    pendingRequestRef.current?.abort();
    pendingRequestRef.current = controller;
    setStreamStatus(null);

    try {
      const activeSessionId = await ensureSessionId(controller.signal);

      if (files.length > 0) {
        if (!activeSessionId) {
          if (!controller.signal.aborted) {
            setAttachmentError("Start a chat before uploading attachments");
          }
          return;
        }

        const ok = await uploadAttachments(activeSessionId, controller.signal);
        if (!ok) return;
      }

      await sendMessage(
        { text: messageText },
        activeSessionId ? { body: { sessionId: activeSessionId } } : undefined
      );
    } catch (err) {
      if (process.env.NODE_ENV === "development") {
        console.error("Failed to submit chat message:", err);
      }
    } finally {
      if (!controller.signal.aborted) {
        setInput("");
      }
      if (pendingRequestRef.current === controller) {
        pendingRequestRef.current = null;
      }
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
        {streamStatus && isLoading ? (
          <div
            className="mb-2 flex items-center gap-2 text-xs text-muted-foreground"
            data-testid="chat-stream-status"
          >
            <span className="inline-flex size-2 animate-pulse rounded-full bg-success/70" />
            <span>
              {streamStatus.step ? `Step ${streamStatus.step}: ` : ""}
              {streamStatus.label}
            </span>
          </div>
        ) : null}

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
              <label className="sr-only" htmlFor={fileInputId}>
                Attach files
              </label>
              <input
                id={fileInputId}
                type="file"
                multiple
                className="sr-only"
                ref={fileInputRef}
                onChange={(e) => {
                  const next = Array.from(e.target.files ?? []);
                  setFiles((prev) => [
                    ...prev,
                    ...next.map((file) => ({ file, id: secureId(16) })),
                  ]);
                  setAttachmentError(null);
                }}
                disabled={isLoading}
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                aria-label="Attach files"
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading}
              >
                <PaperclipIcon aria-hidden="true" className="mr-1 size-4" />
                Attach
              </Button>
              {/* Streaming controls */}
              {isStreaming ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => stop()}
                  aria-label="Stop generation"
                >
                  <StopCircleIcon aria-hidden="true" className="mr-1 size-4" />
                  Stop
                </Button>
              ) : null}

              {/* Regenerate button - only show when ready and there are messages */}
              {status === "ready" && messages.length > 0 ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() =>
                    regenerate(sessionId ? { body: { sessionId } } : undefined)
                  }
                  aria-label="Regenerate response"
                >
                  <RefreshCwIcon aria-hidden="true" className="mr-1 size-4" />
                  Regenerate
                </Button>
              ) : null}
            </div>

            <div className="ml-auto">
              <PromptInputSubmit status={submitStatus} />
            </div>
          </PromptInputFooter>
        </PromptInput>

        {files.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-2" data-testid="chat-attachments">
            {files.map(({ file, id }) => (
              <div
                key={id}
                className="inline-flex items-center gap-2 rounded-md border bg-muted/30 px-2 py-1 text-xs"
              >
                <span className="min-w-0 max-w-[50px] truncate">{file.name}</span>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  aria-label={`Remove ${file.name}`}
                  onClick={() => {
                    setFiles((prev) => prev.filter((entry) => entry.id !== id));
                  }}
                >
                  <XIcon aria-hidden="true" className="size-3" />
                </Button>
              </div>
            ))}
          </div>
        ) : null}

        {attachmentError ? (
          <div className="mt-2 rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {attachmentError}
          </div>
        ) : null}

        {/* Error display with retry */}
        {error ? (
          <div
            className="mt-2 flex items-center justify-between rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2"
            data-testid="chat-error"
          >
            <p className="text-sm text-destructive">{resolveChatErrorMessage(error)}</p>
            <Button
              type="button"
              variant="link"
              size="sm"
              onClick={() =>
                regenerate(sessionId ? { body: { sessionId } } : undefined)
              }
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
