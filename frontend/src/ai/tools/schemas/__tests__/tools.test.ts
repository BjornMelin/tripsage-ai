/** @vitest-environment node */

import { toolExecutionContextSchema } from "@ai/tools/schemas/tools";
import { describe, expect, it } from "vitest";

describe("tool execution schemas", () => {
  describe("toolExecutionContextSchema", () => {
    it("should parse valid tool execution context", () => {
      const validContext = {
        userId: "user-123",
        sessionId: "session-456",
        ip: "192.168.1.1",
      };

      const result = toolExecutionContextSchema.safeParse(validContext);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.userId).toBe("user-123");
        expect(result.data.sessionId).toBe("session-456");
      }
    });

    it("should combine userContextSchema with executionDepsSchema and approvalContextSchema", () => {
      const context = {
        userId: "user-123",
        now: () => Date.now(),
        redis: {},
        requireApproval: () => Promise.resolve(true),
      };

      const result = toolExecutionContextSchema.safeParse(context);
      expect(result.success).toBe(true);
    });

    it("should require userId", () => {
      const invalidContext = {
        sessionId: "session-456",
      };

      const result = toolExecutionContextSchema.safeParse(invalidContext);
      expect(result.success).toBe(false);
    });
  });
});

