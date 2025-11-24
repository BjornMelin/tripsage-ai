/** @vitest-environment node */

import { describe, it, expect } from "vitest";
import { getEmulatorConfig } from "@/test/upstash/emulator";

describe("Upstash emulator contract", () => {
  const config = getEmulatorConfig();
  const shouldRun = config.enabled && !!config.redisUrl && !!config.qstashUrl;

  it.skipIf(!shouldRun)("detects emulator configuration", () => {
    expect(config.redisUrl).toBeDefined();
    expect(config.qstashUrl).toBeDefined();
  });
});
