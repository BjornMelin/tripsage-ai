/**
 * @fileoverview Minimal AI SDK v7 demo page rendering a conversation area and a PromptInput from AI Elements, wired to the demo streaming route.
 */

"use client";

import { useCallback, useState } from "react";
import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
} from "@/components/ai-elements/conversation";
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
} from "@/components/ai-elements/prompt-input";
import { Response } from "@/components/ai-elements/response";
import { MAIN_CONTENT_ID } from "@/lib/a11y/landmarks";

/**
 * Render the AI SDK v7 demo page.
 *
 * Submits user input to `/api/ai/stream` and appends streamed chunks to
 * a preview area. This page intentionally keeps logic minimal for foundations.
 *
 * @returns The demo page component.
 */
export default function AiDemoPage() {
  const [output, setOutput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submitStatus = error ? "error" : isLoading ? "submitted" : undefined;

  const logTelemetry = useCallback((status: "success" | "error", detail?: string) => {
    fetch("/api/telemetry/ai-demo", {
      body: JSON.stringify({ detail, status }),
      headers: { "content-type": "application/json" },
      method: "POST",
    }).catch(() => {
      // Ignore telemetry failures
    });
  }, []);

  /**
   * Handle prompt submission by streaming response from AI API.
   *
   * @param prompt - The user input text to send to the AI service.
   */
  const onSubmit = useCallback(
    async (prompt: string) => {
      setIsLoading(true);
      setOutput("");
      setError(null);
      try {
        const res = await fetch("/api/ai/stream", {
          body: JSON.stringify({ prompt }),
          headers: { "content-type": "application/json" },
          method: "POST",
        });

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }

        const reader = res.body?.getReader();
        if (!reader) {
          throw new Error("Response body is not available");
        }

        const decoder = new TextDecoder();
        let buffer = "";
        let hasTerminalMarker = false;
        let shouldStop = false;
        // Parse UI Message Stream events and append text parts
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true }).replaceAll("\r\n", "\n");
          const events = buffer.split("\n\n");
          // Keep the last partial chunk in buffer
          buffer = events.pop() ?? "";
          for (const evt of events) {
            const lines = evt.split("\n");
            for (const line of lines) {
              const trimmed = line.trim();
              if (!trimmed.startsWith("data:")) continue;
              const data = trimmed.slice(5).trim();
              if (!data) continue;
              if (data === "[DONE]") {
                hasTerminalMarker = true;
                shouldStop = true;
                break;
              }
              let payload: unknown;
              try {
                payload = JSON.parse(data);
              } catch {
                throw new Error("AI stream returned invalid data");
              }
              if (!payload || typeof payload !== "object") continue;
              const chunk = payload as Record<string, unknown>;
              if (chunk.type === "text-delta" && typeof chunk.delta === "string") {
                setOutput((prev) => prev + chunk.delta);
              } else if (chunk.type === "finish") {
                hasTerminalMarker = true;
              } else if (chunk.type === "abort") {
                reader.cancel().catch(() => {
                  // Preserve the generic abort error.
                });
                throw new Error("AI stream was interrupted");
              } else if (chunk.type === "error") {
                reader.cancel().catch(() => {
                  // Preserve the server-provided stream error.
                });
                throw new Error(
                  typeof chunk.errorText === "string" && chunk.errorText.trim()
                    ? chunk.errorText
                    : "AI stream failed"
                );
              }
            }
            if (shouldStop) break;
          }
          if (shouldStop) break;
        }
        if (!hasTerminalMarker) {
          throw new Error("AI stream ended unexpectedly");
        }
        logTelemetry("success");
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Unknown error occurred";
        setError(`Failed to stream response: ${errorMessage}`);
        logTelemetry("error", errorMessage);
      } finally {
        setIsLoading(false);
      }
    },
    [logTelemetry]
  );

  return (
    <main id={MAIN_CONTENT_ID} className="flex h-full flex-col" tabIndex={-1}>
      <Conversation className="min-h-[60vh]">
        <ConversationContent>
          {error ? (
            <div className="text-destructive text-sm p-4 border border-destructive/20 rounded-md bg-destructive/5">
              <strong>Error:</strong> {error}
            </div>
          ) : output ? (
            <Response isAnimating={isLoading}>{output}</Response>
          ) : (
            <ConversationEmptyState description="Type a message and submit to stream a demo response." />
          )}
        </ConversationContent>
      </Conversation>

      <div className="border-t p-2">
        <PromptInput
          onSubmit={async (message) => {
            await onSubmit(message.text ?? "");
          }}
        >
          <PromptInputBody>
            <PromptInputTextarea
              aria-label="Message"
              placeholder="Say hello to AI SDK v7"
              disabled={isLoading}
            />
          </PromptInputBody>
          <PromptInputFooter>
            <PromptInputSubmit disabled={isLoading} status={submitStatus} />
          </PromptInputFooter>
        </PromptInput>
      </div>
    </main>
  );
}
