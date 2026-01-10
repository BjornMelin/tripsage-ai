/** @vitest-environment node */

import { afterEach, describe, expect, it, vi } from "vitest";

type BotIdProtectEnv = {
  basePath?: string;
};

function loadBotIdProtect({ basePath }: BotIdProtectEnv) {
  vi.stubEnv("NEXT_PUBLIC_BASE_PATH", basePath);
  vi.resetModules();
  return import("../botid-protect");
}

describe("config/botid-protect", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns base rules when NEXT_PUBLIC_BASE_PATH is unset", async () => {
    const { getBotIdProtectRules } = await loadBotIdProtect({ basePath: undefined });
    const rules = getBotIdProtectRules();

    expect(rules).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ method: "*", path: "/api/chat*" }),
        expect.objectContaining({ method: "POST", path: "/login" }),
      ])
    );
  });

  it("prefixes rules when NEXT_PUBLIC_BASE_PATH is set", async () => {
    const { getBotIdProtectRules } = await loadBotIdProtect({ basePath: "/app/" });
    const rules = getBotIdProtectRules();

    expect(rules).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ method: "*", path: "/app/api/chat*" }),
        expect.objectContaining({ method: "POST", path: "/app/login" }),
      ])
    );
  });
});
