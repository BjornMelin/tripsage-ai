/**
 * @fileoverview Instruction normalization helpers for AI agents.
 */

import "server-only";

import type { SystemModelMessage } from "ai";

/** Type guard for message parts that may contain text or content strings. */
function isTextPart(part: unknown): part is { text?: string; content?: string } {
  return typeof part === "object" && part !== null;
}

/** Extracts text from the content of a system model message. */
export const extractTextFromContent = (
  content: SystemModelMessage["content"]
): string => {
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";

  const contentArray = content as unknown[];
  const parts = contentArray
    .flatMap((part: unknown) => {
      if (!isTextPart(part)) return [] as string[];
      const texts: string[] = [];
      if (typeof part.text === "string") texts.push(part.text);
      if (typeof part.content === "string") texts.push(part.content);
      return texts;
    })
    .filter(Boolean);

  return parts.length ? parts.join("\n") : "";
};

/** Normalizes the instructions for a system model message. */
export const normalizeInstructions = (input: string | SystemModelMessage): string => {
  if (typeof input === "string") return input;
  return extractTextFromContent(input.content);
};
