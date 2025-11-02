/**
 * @fileoverview Chat page integrating AI Elements primitives with AI SDK v6.
 * Uses the official `useChat` hook to manage UI message streams and state.
 */
"use client";

import { useChat } from "@ai-sdk/react";
import type { FileUIPart, UIMessage } from "ai";
import { DefaultChatTransport } from "ai";
import { type ReactElement, useCallback, useEffect, useMemo, useState } from "react";
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
import { useSupabase } from "@/lib/supabase/client";

/**
 * Resolve the authenticated Supabase user id for the current browser session.
 *
 * @returns The authenticated user's id or null when unauthenticated.
 */
function useCurrentUserId(): string | null {
  const supabase = useSupabase();
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    supabase.auth
      .getUser()
      .then(({ data }) => {
        if (isMounted) {
          setUserId(data.user?.id ?? null);
        }
      })
      .catch(() => {
        if (isMounted) setUserId(null);
      });

    const { data: authListener } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (!isMounted) return;
        setUserId(session?.user?.id ?? null);
      }
    );

    return () => {
      isMounted = false;
      authListener?.subscription.unsubscribe();
    };
  }, [supabase]);

  return userId;
}

/**
 * Render a single chat message including text, tool usage, and metadata parts.
 *
 * @param message UI message streamed by the AI SDK transport.
 * @returns Rendered message content.
 */
function ChatMessageItem({ message }: { message: UIMessage }) {
  const parts = message.parts ?? [];
  return (
    <Message from={message.role} data-testid={`msg-${message.id}`}>
      <MessageAvatar
        src={message.role === "user" ? "/avatar-user.png" : "/avatar-ai.png"}
        name={message.role === "user" ? "You" : "AI"}
      />
      <MessageContent>
        {parts.length > 0 ? (
          parts.map((part, idx) => {
            switch (part?.type) {
              case "text":
                return (
                  <p key={`${message.id}-t-${idx}`} className="whitespace-pre-wrap">
                    {part.text}
                  </p>
                );
              case "tool-call":
              case "tool-call-result":
                return (
                  <div
                    key={`${message.id}-tool-${idx}`}
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
                    key={`${message.id}-r-${idx}`}
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
                  <pre key={`${message.id}-u-${idx}`} className="text-xs opacity-70">
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

/**
 * Chat page component using AI SDK v6 and AI Elements.
 *
 * Manages chat state, user authentication, and message streaming.
 * Filters system messages from display and handles input validation.
 *
 * @returns Chat interface with message history and input controls.
 */
export default function ChatPage(): ReactElement {
  // Get the current authenticated user ID for personalization
  const userId = useCurrentUserId();

  // Create chat transport with user-specific context for API requests
  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: "/api/chat/stream",
        credentials: "include",
        body: () => (userId ? { user_id: userId } : {}),
        // Enable resumable streams by preparing a reconnect request when needed.
        prepareReconnectToStreamRequest: () => ({
          api: "/api/chat/stream",
          credentials: "include",
          headers: undefined,
        }),
      }),
    [userId]
  );

  // Initialize chat state management with AI SDK hooks
  const chatHelpers = useChat({
    id: userId ?? undefined,
    resume: true,
    transport,
  });

  const { messages, sendMessage, status, stop, regenerate, clearError, error } =
    chatHelpers;
  // Experimental resume helper; not part of stable types in all builds.
  const experimental_resume = (
    chatHelpers as unknown as { experimental_resume?: () => Promise<unknown> }
  ).experimental_resume;

  // Surface a brief toast when a resume attempt completes.
  const [showReconnected, setShowReconnected] = useState(false);
  useEffect(() => {
    let mounted = true;
    const fn = experimental_resume as undefined | (() => Promise<unknown>);
    if (typeof fn === "function") {
      void fn()
        .then(() => {
          if (!mounted) return;
          setShowReconnected(true);
          const t = setTimeout(() => setShowReconnected(false), 3000);
          return () => clearTimeout(t);
        })
        .catch(() => {
          /* ignore resume errors */
        });
    }
    return () => {
      mounted = false;
    };
  }, [experimental_resume]);

  // Filter out system messages from display (e.g., tool instructions)
  const visibleMessages = useMemo(
    () => messages.filter((message) => message.role !== "system"),
    [messages]
  );

  /**
   * Handle chat message submission.
   *
   * Validates input, clears errors, and sends message with files to API.
   *
   * @param text - User message text.
   * @param files - Attached files array.
   */
  const handleSubmit = useCallback(
    async ({ text, files }: PromptInputMessage) => {
      const normalizedText = (text ?? "").trim();
      const preparedFiles: FileUIPart[] | undefined =
        files && files.length > 0 ? files : undefined;

      if (!normalizedText && !preparedFiles) {
        return;
      }

      if (status === "error") {
        clearError();
      }

      await sendMessage({
        text: normalizedText,
        files: preparedFiles,
        metadata: userId ? { userId } : undefined,
      });
    },
    [clearError, sendMessage, status, userId]
  );

  // Determine button states based on current chat status
  const canStop = status === "streaming";
  const canRetry = visibleMessages.some((message) => message.role === "assistant");

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      {showReconnected ? (
        <div
          role="status"
          data-testid="reconnected-toast"
          className="fixed right-4 top-4 z-50 rounded-md border bg-green-600/90 px-3 py-2 text-sm text-white shadow"
        >
          Reconnected
        </div>
      ) : null}
      {/* Main conversation area with message history */}
      <Conversation className="flex-1">
        <ConversationContent>
          {visibleMessages.length === 0 ? (
            <ConversationEmptyState description="Start a conversation to see messages here." />
          ) : (
            visibleMessages.map((message) => (
              <ChatMessageItem key={message.id} message={message} />
            ))
          )}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      {/* Input controls and action buttons */}
      <div className="border-t p-2">
        <PromptInputProvider>
          <PromptInput onSubmit={handleSubmit}>
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
              <div className="flex w-full items-center justify-end gap-2">
                <button
                  type="button"
                  aria-label="Stop streaming"
                  className="rounded border px-3 py-1 text-sm disabled:opacity-50"
                  onClick={() => {
                    void stop();
                  }}
                  disabled={!canStop}
                >
                  Stop
                </button>
                <button
                  type="button"
                  aria-label="Retry last request"
                  className="rounded border px-3 py-1 text-sm disabled:opacity-50"
                  onClick={() => {
                    void regenerate();
                  }}
                  disabled={!canRetry || status === "streaming"}
                >
                  Retry
                </button>
                <div className="ml-auto">
                  <PromptInputSubmit status={status} />
                </div>
              </div>
              {error ? (
                <p className="mt-2 text-sm text-destructive">
                  {error.message ?? "Something went wrong. Please try again."}
                </p>
              ) : null}
            </PromptInputFooter>
          </PromptInput>
        </PromptInputProvider>
      </div>
    </div>
  );
}
