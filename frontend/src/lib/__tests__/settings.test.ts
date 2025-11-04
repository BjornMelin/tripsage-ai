import { beforeEach, describe, expect, it } from "vitest";

describe("getProviderSettings", () => {
  const env = process.env;
  beforeEach(() => {
    process.env = { ...env };
  });

  it("maps OPENROUTER_* envs to attribution settings", async () => {
    process.env.OPENROUTER_REFERER = "https://example.com";
    process.env.OPENROUTER_TITLE = "TripSage";
    const { getProviderSettings } = await import("../settings");
    const settings = getProviderSettings();
    expect(settings.openrouterAttribution).toMatchObject({
      referer: "https://example.com",
      title: "TripSage",
    });
  });

  it("treats literal 'undefined' values as unset", async () => {
    process.env.OPENROUTER_REFERER = "undefined" as string | undefined;
    process.env.OPENROUTER_TITLE = "undefined" as string | undefined;
    const { getProviderSettings } = await import("../settings");
    const settings = getProviderSettings();
    expect(settings.openrouterAttribution?.referer).toBeUndefined();
    expect(settings.openrouterAttribution?.title).toBeUndefined();
  });

  it("exposes default provider preference order", async () => {
    const { getProviderSettings } = await import("../settings");
    const settings = getProviderSettings();
    expect(settings.preference).toEqual(["openai", "openrouter", "anthropic", "xai"]);
  });
});
