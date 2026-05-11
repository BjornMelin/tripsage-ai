/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import type { ServerLogger } from "@/lib/telemetry/logger";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { parsePersistedUiParts, rehydrateToolInvocations } from "../_ui-message-parts";

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

  it("rehydrates tool rows as AI SDK v6 static tool UI parts", () => {
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
});
