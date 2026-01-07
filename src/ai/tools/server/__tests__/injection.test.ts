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
      "attachments.list": { execute: vi.fn() },
    };

    const wrapped = wrapToolsWithChatId(tools, undefined, ["attachments.list"]);

    expect(wrapped).toBe(tools);
  });

  it("returns the original tools when onlyKeys is empty", () => {
    const tools = {
      "attachments.list": { execute: vi.fn() },
    };

    const wrapped = wrapToolsWithChatId(tools, "chat-123", []);

    expect(wrapped).toBe(tools);
  });

  it("injects chatId into tool input", async () => {
    const execute = vi.fn(async (input: unknown) => input);
    const tools = {
      "attachments.list": { execute },
    };

    const wrapped = wrapToolsWithChatId(tools, "chat-123", ["attachments.list"]);
    const tool = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped["attachments.list"]
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
      "attachments.list": { execute: wrappedExecute },
      "other.tool": { execute: untouchedExecute },
    };

    const wrapped = wrapToolsWithChatId(tools, "chat-123", ["attachments.list"]);

    const listedTool = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped["attachments.list"]
    );
    const otherTool = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped["other.tool"]
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
      "attachments.list": { execute: execA },
      "attachments.other": { execute: execB },
    };

    const wrapped = wrapToolsWithChatId(tools, "chat-123", [
      "attachments.list",
      "attachments.other",
    ]);

    const toolA = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped["attachments.list"]
    );
    const toolB = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped["attachments.other"]
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
      "trips.savePlace": { execute },
    };

    const wrapped = wrapToolsWithUserId(
      tools,
      "user-abc",
      ["trips.savePlace"],
      "session-xyz"
    );
    const tool = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped["trips.savePlace"]
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
      "trips.savePlace": { execute },
    };

    const wrapped = wrapToolsWithUserId(tools, "user-abc", ["trips.savePlace"]);
    const tool = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped["trips.savePlace"]
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
      "other.tool": { execute: untouchedExecute },
      "trips.savePlace": { execute: wrappedExecute },
    };

    const wrapped = wrapToolsWithUserId(tools, "user-abc", ["trips.savePlace"]);

    const listedTool = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped["trips.savePlace"]
    );
    const otherTool = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped["other.tool"]
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
      "trips.saveAnother": { execute: execB },
      "trips.savePlace": { execute: execA },
    };

    const wrapped = wrapToolsWithUserId(tools, "user-abc", [
      "trips.savePlace",
      "trips.saveAnother",
    ]);

    const toolA = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped["trips.savePlace"]
    );
    const toolB = unsafeCast<{ execute: (input: unknown) => unknown }>(
      wrapped["trips.saveAnother"]
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
      "trips.savePlace": { execute: vi.fn() },
    };

    const wrapped = wrapToolsWithUserId(tools, "user-abc", []);

    expect(wrapped).toBe(tools);
  });
});
