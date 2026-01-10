/** @vitest-environment node */

import { agentConfigRequestSchema } from "@schemas/configuration";
import { describe, expect, it } from "vitest";

describe("agentConfigRequestSchema", () => {
  it("accepts step timeout when total timeout is present", () => {
    const result = agentConfigRequestSchema.safeParse({
      stepTimeoutSeconds: 10,
      timeoutSeconds: 30,
    });

    expect(result.success).toBe(true);
  });

  it("rejects step timeout when total timeout is missing", () => {
    const result = agentConfigRequestSchema.safeParse({
      stepTimeoutSeconds: 10,
    });

    expect(result.success).toBe(false);
  });

  it("rejects step timeout greater than total timeout", () => {
    const result = agentConfigRequestSchema.safeParse({
      stepTimeoutSeconds: 40,
      timeoutSeconds: 30,
    });

    expect(result.success).toBe(false);
  });
});
