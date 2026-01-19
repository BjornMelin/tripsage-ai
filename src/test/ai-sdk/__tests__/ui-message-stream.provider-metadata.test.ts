import { readUIMessageStream, simulateReadableStream, type UIMessageChunk } from "ai";
import { describe, expect, it } from "vitest";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

describe("AI SDK UI message stream provider metadata", () => {
  it("preserves provider metadata on dynamic tool parts during input-streaming", async () => {
    const providerMetadata = {
      openai: {
        mcp: {
          traceId: "trace-1",
        },
      },
    };

    const chunks: UIMessageChunk[] = [
      unsafeCast<UIMessageChunk>({ messageId: "m-1", type: "start" }),
      unsafeCast<UIMessageChunk>({
        dynamic: true,
        providerExecuted: true,
        providerMetadata,
        toolCallId: "tool-call-1",
        toolName: "webSearch",
        type: "tool-input-start",
      }),
    ];

    const stream = simulateReadableStream<UIMessageChunk>({
      chunkDelayInMs: null,
      chunks,
      initialDelayInMs: null,
    });

    const messages: unknown[] = [];
    for await (const message of readUIMessageStream({ stream })) {
      messages.push(message);
    }

    const lastMessage = messages.at(-1) as { parts?: unknown[] } | undefined;
    const parts = Array.isArray(lastMessage?.parts) ? lastMessage.parts : [];

    const dynamicToolPart = parts.find(
      (part) =>
        typeof part === "object" &&
        part !== null &&
        "type" in part &&
        (part as { type?: unknown }).type === "dynamic-tool" &&
        "toolCallId" in part &&
        (part as { toolCallId?: unknown }).toolCallId === "tool-call-1"
    ) as { callProviderMetadata?: unknown; state?: unknown } | undefined;

    expect(dynamicToolPart).toBeDefined();
    expect(dynamicToolPart?.state).toBe("input-streaming");
    expect(dynamicToolPart?.callProviderMetadata).toEqual(providerMetadata);
  });
});
