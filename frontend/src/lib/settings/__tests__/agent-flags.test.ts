import { afterEach, describe, expect, it } from "vitest";

import { __testOnlyReadFlag, getAgentFeatureFlags } from "@/lib/settings/agent-flags";

describe("agent feature flags", () => {
  afterEach(() => {
    process.env.AGENT_WAVE_FLIGHT = undefined;
  });

  it("parses truthy values", () => {
    process.env.AGENT_WAVE_FLIGHT = "true";
    expect(__testOnlyReadFlag("AGENT_WAVE_FLIGHT")).toBe(true);
  });

  it("exposes default flags", () => {
    const flags = getAgentFeatureFlags();
    expect(flags.flights).toBe(false);
    expect(flags.router).toBe(false);
  });
});
