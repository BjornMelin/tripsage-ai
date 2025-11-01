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
  const [input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [_isLoading, setIsLoading] = useState(false);

  const onSubmit = useCallback(async () => {
    setIsLoading(true);
    setOutput("");
    try {
      const res = await fetch("/api/_health/stream", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ prompt: input }),
      });

      const reader = res.body?.getReader();
      if (!reader) return;

      const decoder = new TextDecoder();
      // Naive SSE reader for demo purposes
      // Accumulates streamed chunks into `output`
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        setOutput((prev) => prev + decoder.decode(value));
      }
    } finally {
      setIsLoading(false);
    }
  }, [input]);

  return (
    <div className="flex h-full flex-col">
      <Conversation className="min-h-[60vh]">
        <ConversationContent>
          {output ? (
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
            void onSubmit();
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
