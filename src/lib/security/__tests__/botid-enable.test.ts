/** @vitest-environment node */

import { afterEach, describe, expect, it, vi } from "vitest";
import { isBotIdEnabledForCurrentEnvironment } from "../botid";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("isBotIdEnabledForCurrentEnvironment", () => {
  it("defaults to enabled for production, preview, and test", () => {
    vi.stubEnv("BOTID_ENABLE", undefined);

    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("VERCEL_ENV", undefined);
    expect(isBotIdEnabledForCurrentEnvironment()).toBe(false);

    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("VERCEL_ENV", undefined);
    expect(isBotIdEnabledForCurrentEnvironment()).toBe(true);

    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("VERCEL_ENV", "preview");
    expect(isBotIdEnabledForCurrentEnvironment()).toBe(true);

    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("VERCEL_ENV", undefined);
    expect(isBotIdEnabledForCurrentEnvironment()).toBe(true);
  });

  it("can be enabled for development via BOTID_ENABLE", () => {
    vi.stubEnv("BOTID_ENABLE", "production,preview,development");
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("VERCEL_ENV", undefined);

    expect(isBotIdEnabledForCurrentEnvironment()).toBe(true);
  });
});
