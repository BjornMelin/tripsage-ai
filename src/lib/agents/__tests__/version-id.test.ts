/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { createAgentConfigVersionId } from "@/lib/agents/version-id";

describe("createAgentConfigVersionId", () => {
  it("keeps the existing epoch-second version id shape", () => {
    expect(createAgentConfigVersionId("2026-02-03T04:05:06.000Z", "deadbeef")).toBe(
      "v1770091506_deadbeef"
    );
  });
});
