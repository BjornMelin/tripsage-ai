/**
 * @fileoverview Minimal AI SDK v6 demo page rendering a conversation area and
 * a PromptInput from AI Elements, wired to the demo streaming route.
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

/**
 * Render the AI SDK v6 demo page.
 *
 * Submits user input to `/api/_health/stream` and appends streamed chunks to
 * a preview area. This page intentionally keeps logic minimal for foundations.
 *
 * @returns The demo page component.
 */
export default function AIDemoPage() {
  const [_input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [_isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Handle prompt submission by streaming response from AI API.
   *
   * @param prompt - The user input text to send to the AI service.
   */
  const onSubmit = useCallback(async (prompt: string) => {
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
      // Parse UI Message Stream events and append text parts
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        // Keep the last partial chunk in buffer
        buffer = events.pop() ?? "";
        for (const evt of events) {
          const line = evt.trim();
          if (!line.startsWith("data: ")) continue;
          const json = line.slice(6);
          try {
            const payload = JSON.parse(json) as { type?: string; text?: string };
            if (payload.type === "text" && typeof payload.text === "string") {
              setOutput((prev) => prev + payload.text);
            }
          } catch {
            // Ignore malformed chunks
          }
        }
      }
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Unknown error occurred";
      setError(`Failed to stream response: ${errorMessage}`);
      console.error("Demo page streaming error:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <div className="flex h-full flex-col">
      <Conversation className="min-h-[60vh]">
        <ConversationContent>
          {error ? (
            <div className="text-destructive text-sm p-4 border border-destructive/20 rounded-md bg-destructive/5">
              <strong>Error:</strong> {error}
            </div>
          ) : output ? (
            <pre className="whitespace-pre-wrap text-sm">{output}</pre>
          ) : (
            <ConversationEmptyState description="Type a message and submit to stream a demo response." />
          )}
        </ConversationContent>
      </Conversation>

      <div className="border-t p-2">
        <PromptInput
          onSubmit={(message) => {
            setInput(message.text ?? "");
            void onSubmit(message.text ?? "");
          }}
        >
          <PromptInputBody>
            <PromptInputTextarea placeholder="Say hello to AI SDK v6" />
          </PromptInputBody>
          <PromptInputFooter>
            <PromptInputSubmit />
          </PromptInputFooter>
        </PromptInput>
      </div>
    </div>
  );
}
