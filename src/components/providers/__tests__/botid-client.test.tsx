/** @vitest-environment jsdom */

import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import { getBotIdProtectRules } from "@/config/botid-protect";
import { renderWithProviders, waitFor } from "@/test/test-utils";
import { BotIdClientProvider } from "../botid-client";

const INIT_SPY = vi.hoisted(() => vi.fn());
const ORIGINAL_NODE_ENV = process.env.NODE_ENV;

vi.mock("botid/client/core", () => ({
  initBotId: INIT_SPY,
}));

describe("BotIdClientProvider", () => {
  beforeEach(() => {
    vi.stubEnv("NODE_ENV", "development");
    INIT_SPY.mockClear();
    globalThis.tripsageBotIdClientInitialized = undefined;
    globalThis.tripsageBotIdClientInitFailed = undefined;
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
});
