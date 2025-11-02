/**
 * @fileoverview Tests for AI stream route behavior when prompt exhausts context.
 */

import { describe, expect, it } from "vitest";
import { POST } from "../route";

describe("/api/ai/stream route", () => {
  it("returns 400 when no output tokens are available for the prompt", async () => {
    const huge = "x".repeat(128_000 * 4 + 10_000); // > DEFAULT_CONTEXT_LIMIT under heuristic
    const req = new Request("http://localhost/api/ai/stream", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        model: "some-unknown-model", // forces default context limit
        desiredMaxTokens: 1000,
        messages: [{ role: "user", content: huge }],
      }),
    });

    const res = await POST(req);
    expect(res.status).toBe(400);
    const data = (await res.json()) as any;
    expect(data.error).toMatch(/No output tokens available/i);
    expect(Array.isArray(data.reasons)).toBe(true);
  });
});
