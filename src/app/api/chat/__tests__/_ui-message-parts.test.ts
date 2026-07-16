/** @vitest-environment node */

import { createOpenAI } from "@ai-sdk/openai";
import { convertToModelMessages, generateText, safeValidateUIMessages, tool } from "ai";
import { describe, expect, it, vi } from "vitest";
import { z } from "zod";
import type { ServerLogger } from "@/lib/telemetry/logger";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import {
  parsePersistedUiParts,
  rehydrateToolInvocations,
  sanitizePersistableUiParts,
} from "../_ui-message-parts";

describe("chat UI message part persistence", () => {
  it("drops persisted tool-shaped parts and keeps canonical non-tool parts", () => {
    const parts = parsePersistedUiParts({
      content: JSON.stringify([
        { text: "hello", type: "text" },
        { type: "step-start" },
        { data: { kind: "start", label: "Thinking" }, type: "data-status" },
        {
          input: { query: "london" },
          toolCallId: "call-1",
          toolName: "webSearch",
          type: "tool-call",
        },
        {
          output: { ok: true },
          toolCallId: "call-1",
          type: "tool-result",
        },
        {
          input: { query: "paris" },
          state: "input-available",
          toolCallId: "call-2",
          toolName: "webSearch",
          type: "dynamic-tool",
        },
        {
          input: { query: "rome" },
          state: "input-available",
          toolCallId: "call-3",
          type: "tool-webSearch",
        },
        { toolCallId: "call-4", type: "tool-input-start" },
      ]),
      messageDbId: 1,
      sessionId: "session-1",
    });

    expect(parts).toEqual([
      { text: "hello", type: "text" },
      { type: "step-start" },
      {
        data: { kind: "start", label: "Thinking" },
        id: undefined,
        type: "data-status",
      },
    ]);
  });

  it("falls back to a text part when stored JSON is invalid", () => {
    const warn = vi.fn();
    const logger = unsafeCast<ServerLogger>({ warn });

    const parts = parsePersistedUiParts({
      content: "[not-json",
      logger,
      messageDbId: 2,
      sessionId: "session-1",
    });

    expect(parts).toEqual([{ text: "[not-json", type: "text" }]);
    expect(warn).toHaveBeenCalledWith(
      "chat:stored_parts_parse_failed",
      expect.objectContaining({
        messageDbId: 2,
        sessionId: "session-1",
      })
    );
    expect(warn.mock.calls[0]?.[1]).not.toHaveProperty("content");
    expect(warn.mock.calls[0]?.[1]).not.toHaveProperty("rawContent");
  });

  it("keeps safe reasoning files and drops malformed or unsafe file parts", () => {
    const parts = parsePersistedUiParts({
      content: JSON.stringify([
        {
          mediaType: " IMAGE/PNG ",
          type: "reasoning-file",
          url: "data:image/png;base64,aGVsbG8=",
        },
        {
          mediaType: "application/pdf",
          type: "reasoning-file",
          url: "https://example.com/reasoning.pdf",
        },
        {
          mediaType: "image",
          type: "file",
          url: "https://example.com/generated-image",
        },
        {
          mediaType: "image/png",
          type: "reasoning-file",
          url: "javascript:alert(1)",
        },
        {
          mediaType: "image/png",
          type: "reasoning-file",
          url: "data:text/plain;base64,aGVsbG8=",
        },
        {
          mediaType: "image/png",
          type: "reasoning-file",
          url: "data:image/png;base64,not-base64!",
        },
        {
          mediaType: "not a media type",
          type: "reasoning-file",
          url: "https://example.com/file",
        },
        {
          mediaType: "image/*",
          type: "reasoning-file",
          url: "https://example.com/file",
        },
      ]),
      messageDbId: 3,
      sessionId: "session-1",
    });

    expect(parts).toEqual([
      {
        mediaType: "image/png",
        type: "reasoning-file",
        url: "data:image/png;base64,aGVsbG8=",
      },
      {
        mediaType: "application/pdf",
        type: "reasoning-file",
        url: "https://example.com/reasoning.pdf",
      },
      {
        filename: undefined,
        mediaType: "image",
        type: "file",
        url: "https://example.com/generated-image",
      },
    ]);
  });

  it("round-trips only supported OpenAI continuation metadata and compaction", async () => {
    const storedContent = JSON.stringify(
      sanitizePersistableUiParts([
        {
          providerMetadata: {
            openai: { itemId: "text-item-1", phase: "final_answer" },
            untrusted: { blob: "drop-me" },
          },
          text: "Answer",
          type: "text",
        },
        {
          providerMetadata: {
            openai: {
              itemId: "reasoning-item-1",
              reasoningEncryptedContent: "encrypted-reasoning",
              responseId: "drop-me",
            },
          },
          text: "Summary",
          type: "reasoning",
        },
        {
          providerMetadata: {
            openai: {
              itemId: "reasoning-item-2",
              reasoningEncryptedContent: null,
            },
          },
          text: "Unencrypted summary",
          type: "reasoning",
        },
        {
          kind: "openai.compaction",
          providerMetadata: {
            openai: {
              encryptedContent: "encrypted-compaction",
              itemId: "compaction-item-1",
              type: "compaction",
              unsafe: "drop-me",
            },
          },
          type: "custom",
        },
        {
          kind: "openai.compaction",
          providerMetadata: {
            openai: { encryptedContent: "missing-item", type: "compaction" },
          },
          type: "custom",
        },
        {
          kind: "other.unsupported",
          providerMetadata: { other: { itemId: "drop-me" } },
          type: "custom",
        },
      ])
    );
    const parts = parsePersistedUiParts({
      content: storedContent,
      messageDbId: 4,
      sessionId: "session-1",
    });

    expect(parts).toEqual([
      {
        providerMetadata: { openai: { itemId: "text-item-1" } },
        text: "Answer",
        type: "text",
      },
      {
        providerMetadata: {
          openai: {
            itemId: "reasoning-item-1",
            reasoningEncryptedContent: "encrypted-reasoning",
          },
        },
        text: "Summary",
        type: "reasoning",
      },
      {
        providerMetadata: {
          openai: {
            itemId: "reasoning-item-2",
            reasoningEncryptedContent: null,
          },
        },
        text: "Unencrypted summary",
        type: "reasoning",
      },
      {
        kind: "openai.compaction",
        providerMetadata: {
          openai: {
            encryptedContent: "encrypted-compaction",
            itemId: "compaction-item-1",
            type: "compaction",
          },
        },
        type: "custom",
      },
    ]);

    const validated = await safeValidateUIMessages({
      messages: [{ id: "assistant-1", parts, role: "assistant" }],
    });
    expect(validated.success).toBe(true);
    if (!validated.success) throw validated.error;

    await expect(convertToModelMessages(validated.data)).resolves.toEqual([
      {
        content: [
          {
            providerOptions: { openai: { itemId: "text-item-1" } },
            text: "Answer",
            type: "text",
          },
          {
            providerOptions: {
              openai: {
                itemId: "reasoning-item-1",
                reasoningEncryptedContent: "encrypted-reasoning",
              },
            },
            text: "Summary",
            type: "reasoning",
          },
          {
            providerOptions: {
              openai: {
                itemId: "reasoning-item-2",
                reasoningEncryptedContent: null,
              },
            },
            text: "Unencrypted summary",
            type: "reasoning",
          },
          {
            kind: "openai.compaction",
            providerOptions: {
              openai: {
                encryptedContent: "encrypted-compaction",
                itemId: "compaction-item-1",
                type: "compaction",
              },
            },
            type: "custom",
          },
        ],
        role: "assistant",
      },
    ]);
  });

  it("rehydrates tool rows as AI SDK v7 static tool UI parts", () => {
    const parts = rehydrateToolInvocations([
      {
        arguments: { query: "london" },
        provider_executed: true,
        result: { ok: true },
        status: "completed",
        tool_id: "call-1",
        tool_name: "webSearch",
      },
    ]);

    expect(parts).toEqual([
      {
        input: { query: "london" },
        output: { ok: true },
        providerExecuted: true,
        state: "output-available",
        toolCallId: "call-1",
        type: "tool-webSearch",
      },
    ]);
    expect(parts[0]).not.toHaveProperty("toolName");
  });

  it("sends corrected legacy app tools as OpenAI function call outputs", async () => {
    const parts = rehydrateToolInvocations([
      {
        arguments: { query: "london" },
        provider_executed: false,
        result: { ok: true },
        status: "completed",
        tool_id: "call-legacy-1",
        tool_name: "webSearch",
      },
    ]);
    const tools = {
      webSearch: tool({
        description: "Search the web",
        inputSchema: z.object({ query: z.string() }),
      }),
    };
    const validated = await safeValidateUIMessages({
      messages: [{ id: "assistant-legacy", parts, role: "assistant" }],
    });
    expect(validated.success).toBe(true);
    if (!validated.success) throw validated.error;

    const modelMessages = await convertToModelMessages(validated.data, { tools });
    let requestBody: unknown;
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      requestBody = JSON.parse(String(init?.body)) as unknown;
      return Promise.reject(new Error("request captured"));
    });
    const model = createOpenAI({ apiKey: "test", fetch: fetchMock }).responses(
      "gpt-5.4-mini"
    );

    await expect(
      generateText({ messages: modelMessages, model, tools })
    ).rejects.toThrow("request captured");

    const request = z
      .looseObject({
        input: z.array(z.record(z.string(), z.unknown())),
      })
      .parse(requestBody);
    expect(request.input.map((item) => item.type)).toEqual([
      "function_call",
      "function_call_output",
    ]);
    expect(request.input.every((item) => item.call_id === "call-legacy-1")).toBe(true);
    expect(request.input.some((item) => item.type === "item_reference")).toBe(false);
  });
});
