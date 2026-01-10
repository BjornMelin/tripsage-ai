/**
 * @vitest-environment node
 */

import { describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { wrapToolsWithChatId, wrapToolsWithUserId } from "../injection";

describe("wrapToolsWithChatId", () => {
  it("returns the original tools when chatId is missing", () => {
    const tools = {
      attachmentsList: { execute: vi.fn() },
    };

    const wrapped = wrapToolsWithChatId(tools, undefined, ["attachmentsList"]);

    expect(wrapped).toBe(tools);
  });

  it("returns the original tools when onlyKeys is empty", () => {
    const tools = {
      attachmentsList: { execute: vi.fn() },
    };

    const wrapped = wrapToolsWithChatId(tools, "chat-123", []);

    expect(wrapped).toBe(tools);
  });

  it("injects chatId into tool input", async () => {
    const execute = vi.fn(async (input: unknown) => input);
    const tools = {
      attachmentsList: { execute },
    };

    const wrapped = wrapToolsWithChatId(tools, "chat-123", ["attachmentsList"]);
    const tool = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped.attachmentsList
    );

    await tool.execute({ limit: 5 });

    expect(execute).toHaveBeenCalledWith(
      expect.objectContaining({ chatId: "chat-123", limit: 5 }),
      undefined
    );
  });

  it("does not wrap tools not listed in onlyKeys", async () => {
    const wrappedExecute = vi.fn(async (input: unknown) => input);
    const untouchedExecute = vi.fn(async (input: unknown) => input);
    const tools = {
      attachmentsList: { execute: wrappedExecute },
      otherTool: { execute: untouchedExecute },
    };

    const wrapped = wrapToolsWithChatId(tools, "chat-123", ["attachmentsList"]);

    const listedTool = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped.attachmentsList
    );
    const otherTool = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped.otherTool
    );

    await listedTool.execute({ limit: 1 });
    await otherTool.execute({ foo: "bar" });

    expect(wrappedExecute).toHaveBeenCalledWith(
      expect.objectContaining({ chatId: "chat-123", limit: 1 }),
      undefined
    );
    expect(untouchedExecute).toHaveBeenCalledWith({ foo: "bar" });
  });

  it("wraps all tools listed in onlyKeys", async () => {
    const execA = vi.fn(async (input: unknown) => input);
    const execB = vi.fn(async (input: unknown) => input);
    const tools = {
      attachmentsList: { execute: execA },
      attachmentsOther: { execute: execB },
    };

    const wrapped = wrapToolsWithChatId(tools, "chat-123", [
      "attachmentsList",
      "attachmentsOther",
    ]);

    const toolA = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped.attachmentsList
    );
    const toolB = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped.attachmentsOther
    );

    await toolA.execute({ limit: 2 });
    await toolB.execute({ limit: 3 });

    expect(execA).toHaveBeenCalledWith(
      expect.objectContaining({ chatId: "chat-123", limit: 2 }),
      undefined
    );
    expect(execB).toHaveBeenCalledWith(
      expect.objectContaining({ chatId: "chat-123", limit: 3 }),
      undefined
    );
  });
});

describe("wrapToolsWithUserId", () => {
  it("injects userId and sessionId into tool input", async () => {
    const execute = vi.fn(async (input: unknown) => input);
    const tools = {
      tripsSavePlace: { execute },
    };

    const wrapped = wrapToolsWithUserId(
      tools,
      "user-abc",
      ["tripsSavePlace"],
      "session-xyz"
    );
    const tool = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped.tripsSavePlace
    );

    await tool.execute({ placeId: "place-1" });

    expect(execute).toHaveBeenCalledWith(
      expect.objectContaining({
        placeId: "place-1",
        sessionId: "session-xyz",
        userId: "user-abc",
      }),
      undefined
    );
  });

  it("injects only userId when sessionId is missing", async () => {
    const execute = vi.fn(async (input: unknown) => input);
    const tools = {
      tripsSavePlace: { execute },
    };

    const wrapped = wrapToolsWithUserId(tools, "user-abc", ["tripsSavePlace"]);
    const tool = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped.tripsSavePlace
    );

    await tool.execute({ placeId: "place-1" });

    expect(execute).toHaveBeenCalledWith(
      expect.objectContaining({
        placeId: "place-1",
        userId: "user-abc",
      }),
      undefined
    );
    expect(execute).not.toHaveBeenCalledWith(
      expect.objectContaining({ sessionId: expect.anything() }),
      undefined
    );
  });

  it("does not wrap tools not listed in onlyKeys", async () => {
    const wrappedExecute = vi.fn(async (input: unknown) => input);
    const untouchedExecute = vi.fn(async (input: unknown) => input);
    const tools = {
      otherTool: { execute: untouchedExecute },
      tripsSavePlace: { execute: wrappedExecute },
    };

    const wrapped = wrapToolsWithUserId(tools, "user-abc", ["tripsSavePlace"]);

    const listedTool = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped.tripsSavePlace
    );
    const otherTool = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped.otherTool
    );

    await listedTool.execute({ placeId: "place-2" });
    await otherTool.execute({ foo: "bar" });

    expect(wrappedExecute).toHaveBeenCalledWith(
      expect.objectContaining({ placeId: "place-2", userId: "user-abc" }),
      undefined
    );
    expect(untouchedExecute).toHaveBeenCalledWith({ foo: "bar" });
  });

  it("wraps all tools listed in onlyKeys", async () => {
    const execA = vi.fn(async (input: unknown) => input);
    const execB = vi.fn(async (input: unknown) => input);
    const tools = {
      tripsSaveAnother: { execute: execB },
      tripsSavePlace: { execute: execA },
    };

    const wrapped = wrapToolsWithUserId(tools, "user-abc", [
      "tripsSavePlace",
      "tripsSaveAnother",
    ]);

    const toolA = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped.tripsSavePlace
    );
    const toolB = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped.tripsSaveAnother
    );

    await toolA.execute({ placeId: "place-1" });
    await toolB.execute({ placeId: "place-2" });

    expect(execA).toHaveBeenCalledWith(
      expect.objectContaining({ placeId: "place-1", userId: "user-abc" }),
      undefined
    );
    expect(execB).toHaveBeenCalledWith(
      expect.objectContaining({ placeId: "place-2", userId: "user-abc" }),
      undefined
    );
  });

  it("returns the original tools when onlyKeys is empty", () => {
    const tools = {
      tripsSavePlace: { execute: vi.fn() },
    };

    const wrapped = wrapToolsWithUserId(tools, "user-abc", []);

    expect(wrapped).toBe(tools);
  });
});
