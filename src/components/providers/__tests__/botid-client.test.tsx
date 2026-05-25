/** @vitest-environment jsdom */

import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import { getBotIdProtectRules } from "@/config/botid-protect";
import { renderWithProviders, waitFor } from "@/test/test-utils";
import { BotIdClientProvider } from "../botid-client";

const INIT_SPY = vi.hoisted(() => vi.fn());
const RECORD_CLIENT_ERROR_SPY = vi.hoisted(() => vi.fn());
const ORIGINAL_NODE_ENV = process.env.NODE_ENV;

vi.mock("botid/client/core", () => ({
  initBotId: INIT_SPY,
}));

vi.mock("@/lib/telemetry/client-errors", () => ({
  recordClientErrorOnActiveSpan: RECORD_CLIENT_ERROR_SPY,
}));

describe("BotIdClientProvider", () => {
  beforeEach(() => {
    vi.stubEnv("NODE_ENV", "development");
    INIT_SPY.mockReset();
    RECORD_CLIENT_ERROR_SPY.mockReset();
    globalThis.tripsageBotIdClientInitialized = undefined;
    globalThis.tripsageBotIdClientInitFailed = undefined;
    globalThis.tripsageBotIdClientInitError = undefined;
  });

  afterAll(() => {
    vi.stubEnv("NODE_ENV", ORIGINAL_NODE_ENV);
  });

  it("initializes BotID with configured protected routes", async () => {
    renderWithProviders(<BotIdClientProvider />);

    await waitFor(() => expect(INIT_SPY).toHaveBeenCalledTimes(1));
    expect(INIT_SPY).toHaveBeenCalledWith({ protect: getBotIdProtectRules() });
  });

  it("does not initialize BotID more than once", async () => {
    renderWithProviders(<BotIdClientProvider />);
    renderWithProviders(<BotIdClientProvider />);

    await waitFor(() => expect(INIT_SPY).toHaveBeenCalledTimes(1));
  });

  it("reports early instrumentation initialization failures through telemetry", async () => {
    const earlyError = new Error("early init unavailable");
    globalThis.tripsageBotIdClientInitFailed = true;
    globalThis.tripsageBotIdClientInitError = earlyError;

    renderWithProviders(<BotIdClientProvider />);

    await waitFor(() => {
      expect(RECORD_CLIENT_ERROR_SPY).toHaveBeenCalledWith(earlyError, {
        action: "instrumentation-client",
        context: "BotIdClientProvider",
      });
    });
    expect(INIT_SPY).toHaveBeenCalledTimes(1);
    expect(globalThis.tripsageBotIdClientInitFailed).toBe(false);
    expect(globalThis.tripsageBotIdClientInitError).toBeUndefined();
  });

  it("reports provider initialization failures through telemetry", async () => {
    const initError = new Error("provider init unavailable");
    INIT_SPY.mockImplementationOnce(() => {
      throw initError;
    });

    renderWithProviders(<BotIdClientProvider />);

    await waitFor(() => {
      expect(RECORD_CLIENT_ERROR_SPY).toHaveBeenCalledWith(initError, {
        action: "ensureBotIdClientInitialized",
        context: "BotIdClientProvider",
      });
    });
    expect(globalThis.tripsageBotIdClientInitFailed).toBeUndefined();
    expect(globalThis.tripsageBotIdClientInitError).toBeUndefined();
  });
});
