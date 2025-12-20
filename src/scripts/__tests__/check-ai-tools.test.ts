/** @vitest-environment node */

import { beforeAll, describe, expect, it } from "vitest";

let detectRawToolUsage: typeof import("../../../scripts/check-ai-tools.mjs").detectRawToolUsage;

beforeAll(async () => {
  ({ detectRawToolUsage } = await import("../../../scripts/check-ai-tools.mjs"));
});

describe("check-ai-tools guardrails", () => {
  it("ignores tool() mentions in comments and strings", () => {
    const content = `
      // tool(
      const msg = "tool(";
      const tpl = \`tool(\`;
      /*
        tool(
      */
      export const value = 1;
    `;

    const result = detectRawToolUsage(content);
    expect(result.hasToolCall).toBe(false);
    expect(result.hasToolImport).toBe(false);
  });

  it("detects actual tool() usage in code", () => {
    const content = `
      import { tool } from "ai";
      const myTool = tool({ description: "x" });
      export { myTool };
    `;

    const result = detectRawToolUsage(content);
    expect(result.hasToolImport).toBe(true);
    expect(result.hasToolCall).toBe(true);
  });
});
