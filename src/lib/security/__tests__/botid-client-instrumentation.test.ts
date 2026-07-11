/** @vitest-environment jsdom */

import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";

const { INIT_SPY, PATCH_PERFORMANCE_SPY } = vi.hoisted(() => ({
  INIT_SPY: vi.fn(),
  PATCH_PERFORMANCE_SPY: vi.fn(),
}));

const ORIGINAL_NODE_ENV = process.env.NODE_ENV;

vi.mock("botid/client/core", () => ({
  initBotId: INIT_SPY,
}));

vi.mock("@/lib/performance/patch-performance-measure", () => ({
  patchPerformanceMeasureForPrerender: PATCH_PERFORMANCE_SPY,
}));

describe("client instrumentation BotID gate", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv("NODE_ENV", "development");
    INIT_SPY.mockReset();
    PATCH_PERFORMANCE_SPY.mockReset();
    globalThis.tripsageBotIdClientInitialized = undefined;
    globalThis.tripsageBotIdClientInitFailed = undefined;
    globalThis.tripsageBotIdClientInitError = undefined;
    document.documentElement.removeAttribute("data-botid-enabled");
  });

  afterAll(() => {
    vi.stubEnv("NODE_ENV", ORIGINAL_NODE_ENV);
  });

  it("leaves local fetch instrumentation untouched when BotID is disabled", async () => {
    document.documentElement.dataset.botidEnabled = "false";

    await import("@/instrumentation-client");

    expect(PATCH_PERFORMANCE_SPY).toHaveBeenCalledTimes(1);
    expect(INIT_SPY).not.toHaveBeenCalled();
  });

  it("fails closed when the server decision marker is absent", async () => {
    await import("@/instrumentation-client");

    expect(PATCH_PERFORMANCE_SPY).toHaveBeenCalledTimes(1);
    expect(INIT_SPY).not.toHaveBeenCalled();
  });

  it("initializes BotID once when the server decision enables it", async () => {
    document.documentElement.dataset.botidEnabled = "true";

    await import("@/instrumentation-client");

    expect(PATCH_PERFORMANCE_SPY).toHaveBeenCalledTimes(1);
    expect(INIT_SPY).toHaveBeenCalledTimes(1);
  });
});
