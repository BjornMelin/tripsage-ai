import { describe, expect, it, vi } from "vitest";

import { z } from "zod";
import { runWithGuardrails } from "@/lib/agents";

vi.mock("@/lib/cache/upstash", () => ({
  getCachedJson: vi.fn().mockResolvedValue(null),
  setCachedJson: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/lib/telemetry/agents", () => ({
  recordAgentToolEvent: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/lib/redis", () => ({
  getRedis: () => undefined,
}));

describe("runWithGuardrails", () => {
  it("validates input before executing", async () => {
    await expect(
      runWithGuardrails(
        {
          inputSchema: z.object({ foo: z.string() }),
          tool: "demo",
          workflow: "destination_research",
        },
        { foo: 123 },
        async () => "ok"
      )
    ).rejects.toThrow();
  });

  it("returns result when guardrails pass", async () => {
    const { result, cacheHit } = await runWithGuardrails(
      {
        inputSchema: z.object({ foo: z.string() }),
        tool: "demo",
        workflow: "destination_research",
      },
      { foo: "bar" },
      async () => "ok"
    );
    expect(result).toBe("ok");
    expect(cacheHit).toBe(false);
  });
});
