/** @vitest-environment node */

import { afterEach, describe, expect, it, vi } from "vitest";

type BotProtectionEnv = {
  botidEnable?: string;
  nodeEnv?: string;
  vercelEnv?: string;
};

function loadBotProtection({ botidEnable, nodeEnv, vercelEnv }: BotProtectionEnv) {
  vi.stubEnv("BOTID_ENABLE", botidEnable);
  vi.stubEnv("NODE_ENV", nodeEnv);
  vi.stubEnv("VERCEL_ENV", vercelEnv);
  vi.resetModules();
  return import("../bot-protection");
}

describe("config/bot-protection", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("enables BotId by default in production", async () => {
    const { SHOULD_ENABLE_BOT_ID } = await loadBotProtection({
      botidEnable: undefined,
      nodeEnv: "production",
      vercelEnv: undefined,
    });
    expect(SHOULD_ENABLE_BOT_ID).toBe(true);
  });

  it("enables BotId by default in preview", async () => {
    const { SHOULD_ENABLE_BOT_ID } = await loadBotProtection({
      botidEnable: undefined,
      nodeEnv: "production",
      vercelEnv: "preview",
    });
    expect(SHOULD_ENABLE_BOT_ID).toBe(true);
  });

  it("disables BotId by default in development", async () => {
    const { SHOULD_ENABLE_BOT_ID } = await loadBotProtection({
      botidEnable: undefined,
      nodeEnv: "development",
      vercelEnv: undefined,
    });
    expect(SHOULD_ENABLE_BOT_ID).toBe(false);
  });

  it("disables BotId by default in test", async () => {
    const { SHOULD_ENABLE_BOT_ID } = await loadBotProtection({
      botidEnable: undefined,
      nodeEnv: "test",
      vercelEnv: undefined,
    });
    expect(SHOULD_ENABLE_BOT_ID).toBe(false);
  });

  it("supports BOTID_ENABLE comma-separated overrides", async () => {
    const { SHOULD_ENABLE_BOT_ID: shouldEnableInDev } = await loadBotProtection({
      botidEnable: "development,test",
      nodeEnv: "development",
      vercelEnv: undefined,
    });
    expect(shouldEnableInDev).toBe(true);

    const { SHOULD_ENABLE_BOT_ID: shouldEnableInTest } = await loadBotProtection({
      botidEnable: "development,test",
      nodeEnv: "test",
      vercelEnv: undefined,
    });
    expect(shouldEnableInTest).toBe(true);

    const { SHOULD_ENABLE_BOT_ID: shouldEnableInProd } = await loadBotProtection({
      botidEnable: "development,test",
      nodeEnv: "production",
      vercelEnv: undefined,
    });
    expect(shouldEnableInProd).toBe(false);
  });

  it("treats empty BOTID_ENABLE as fallback to defaults", async () => {
    const { SHOULD_ENABLE_BOT_ID: shouldEnableInProd } = await loadBotProtection({
      botidEnable: "",
      nodeEnv: "production",
      vercelEnv: undefined,
    });
    expect(shouldEnableInProd).toBe(true);

    const { SHOULD_ENABLE_BOT_ID: shouldEnableInTest } = await loadBotProtection({
      botidEnable: "",
      nodeEnv: "test",
      vercelEnv: undefined,
    });
    expect(shouldEnableInTest).toBe(false);
  });

  it("treats whitespace-only BOTID_ENABLE as fallback to defaults", async () => {
    const { SHOULD_ENABLE_BOT_ID: shouldEnableInPreview } = await loadBotProtection({
      botidEnable: "   ",
      nodeEnv: "production",
      vercelEnv: "preview",
    });
    expect(shouldEnableInPreview).toBe(true);
  });

  it("treats comma-only BOTID_ENABLE as no environments enabled", async () => {
    const { SHOULD_ENABLE_BOT_ID } = await loadBotProtection({
      botidEnable: ",,,",
      nodeEnv: "production",
      vercelEnv: undefined,
    });
    expect(SHOULD_ENABLE_BOT_ID).toBe(false);
  });

  it("supports explicit environment inclusion and exclusion", async () => {
    const { SHOULD_ENABLE_BOT_ID: shouldEnableInPreview } = await loadBotProtection({
      botidEnable: "preview",
      nodeEnv: "production",
      vercelEnv: "preview",
    });
    expect(shouldEnableInPreview).toBe(true);

    const { SHOULD_ENABLE_BOT_ID: shouldEnableInProd } = await loadBotProtection({
      botidEnable: "preview",
      nodeEnv: "production",
      vercelEnv: undefined,
    });
    expect(shouldEnableInProd).toBe(false);
  });
});
