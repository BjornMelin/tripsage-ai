/** @vitest-environment node */

import { afterEach, describe, expect, it, vi } from "vitest";
import { isBotIdEnabledForCurrentEnvironment } from "../botid";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("isBotIdEnabledForCurrentEnvironment", () => {
  describe.each([
    { expected: false, nodeEnv: "development", vercelEnv: undefined },
    { expected: true, nodeEnv: "production", vercelEnv: undefined },
    { expected: true, nodeEnv: "production", vercelEnv: "preview" },
    { expected: true, nodeEnv: "test", vercelEnv: undefined },
  ])("defaults for NODE_ENV=$nodeEnv, VERCEL_ENV=$vercelEnv", ({
    nodeEnv,
    vercelEnv,
    expected,
  }) => {
    it(`returns ${expected}`, () => {
      vi.stubEnv("BOTID_ENABLE", undefined);
      vi.stubEnv("NODE_ENV", nodeEnv);
      vi.stubEnv("VERCEL_ENV", vercelEnv);
      expect(isBotIdEnabledForCurrentEnvironment()).toBe(expected);
    });
  });

  it("can be enabled for development via BOTID_ENABLE", () => {
    vi.stubEnv("BOTID_ENABLE", "production,preview,development");
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("VERCEL_ENV", undefined);

    expect(isBotIdEnabledForCurrentEnvironment()).toBe(true);
  });
});
