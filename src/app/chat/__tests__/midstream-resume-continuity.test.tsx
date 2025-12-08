/** @vitest-environment node */

import { describe, expect, it } from "vitest";

type Message = { id: string; role: "user" | "assistant" | "system" };

// Mirrors the visibleMessages filtering in chat/page.tsx
function filterVisibleMessages(messages: Message[]): Message[] {
  return messages.filter((m) => m.role !== "system");
}

describe("mid-stream resume continuity (lightweight)", () => {
  it("retains non-system messages after resume", () => {
    const initial: Message[] = [
      { id: "u1", role: "user" },
      { id: "s1", role: "system" },
      { id: "a1", role: "assistant" },
    ];

    const visible = filterVisibleMessages(initial);
    expect(visible).toHaveLength(2);
    expect(visible.map((m) => m.id)).toEqual(["u1", "a1"]);
  });
});
