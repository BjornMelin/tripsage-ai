/** @vitest-environment node */

import type { SystemModelMessage } from "ai";
import { describe, expect, it } from "vitest";

import { extractTextFromContent, normalizeInstructions } from "../chat-agent";

describe("normalizeInstructions", () => {
  it("returns plain string input unchanged", () => {
    expect(normalizeInstructions("hello world")).toBe("hello world");
  });

  it("joins text parts from structured content", () => {
    const systemMsg = {
      content: [
        { text: "Line one", type: "text" },
        { text: "Line two", type: "text" },
      ],
      role: "system",
    } as unknown as SystemModelMessage;

    expect(normalizeInstructions(systemMsg)).toBe("Line one\nLine two");
  });

  it("falls back to empty string when no text content present", () => {
    const systemMsg = {
      content: [{ type: "image", url: "https://example.com/image.png" }],
      role: "system",
    } as unknown as SystemModelMessage;

    expect(normalizeInstructions(systemMsg)).toBe("");
  });
});

describe("extractTextFromContent", () => {
  it("extracts text from nested content fields", () => {
    const content = [
      { text: "alpha" },
      { content: "beta" },
      { content: "ignored", text: "gamma" },
    ];

    expect(
      extractTextFromContent(content as unknown as SystemModelMessage["content"])
    ).toBe("alpha\nbeta\ngamma\nignored");
  });
});
