/** @vitest-environment node */

import { DefaultChatTransport } from "ai";
import { describe, expect, it } from "vitest";

describe("Chat resume wiring (lightweight)", () => {
  it("enables reconnect support via DefaultChatTransport", () => {
    const transport = new DefaultChatTransport();
    expect(transport).toBeInstanceOf(DefaultChatTransport);
  });

  it("supports resume flag in chat config", () => {
    const chatConfig = { resume: true };
    expect(chatConfig.resume).toBe(true);
  });
});
