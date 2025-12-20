/** @vitest-environment node */

import type { SystemModelMessage } from "ai";
import { describe, expect, it } from "vitest";

import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { extractTextFromContent, normalizeInstructions } from "../instructions";

describe("normalizeInstructions", () => {
  it("returns plain string input unchanged", () => {
    expect(normalizeInstructions("hello world")).toBe("hello world");
  });

  it("joins text parts from structured content", () => {
    const systemMsg = unsafeCast<SystemModelMessage>({
      content: [
        { text: "Line one", type: "text" },
        { text: "Line two", type: "text" },
      ],
      role: "system",
    });

    expect(normalizeInstructions(systemMsg)).toBe("Line one\nLine two");
  });

  it("falls back to empty string when no text content present", () => {
    const systemMsg = unsafeCast<SystemModelMessage>({
      content: [{ type: "image", url: "https://example.com/image.png" }],
      role: "system",
    });

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
      extractTextFromContent(unsafeCast<SystemModelMessage["content"]>(content))
    ).toBe("alpha\nbeta\ngamma\nignored");
  });
});
