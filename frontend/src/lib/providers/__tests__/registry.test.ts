/**
 * @fileoverview Unit tests for provider registry resolution.
 */

import { afterEach, beforeEach, describe, expect, it, type Mock, vi } from "vitest";

vi.mock("@/lib/supabase/rpc", () => ({
  getUserApiKey: vi.fn(),
}));

// Mock provider factories to return simple tagged model ids for assertions.
vi.mock("@ai-sdk/openai", () => ({
  createOpenAI: (opts: { apiKey?: string; baseURL?: string }) => (id: string) =>
    `openai(${opts.baseURL ?? "api.openai.com"})::${opts.apiKey ? "key" : "no-key"}::${id}`,
}));

vi.mock("@ai-sdk/anthropic", () => ({
  anthropic: (id: string) => `anthropic::${id}`,
  createAnthropic: (opts: { apiKey?: string }) => (id: string) =>
    `anthropic::${opts.apiKey ? "key" : "no-key"}::${id}`,
}));

// No direct OpenRouter provider usage in registry; we use OpenAI-compatible client.

describe("resolveProvider", () => {
  const env = process.env;
  beforeEach(() => {
    vi.resetModules();
    process.env = {
      ...env,
      OPENROUTER_REFERER: "https://example.com",
      OPENROUTER_TITLE: "TripSage",
    };
  });
  afterEach(() => {
    process.env = env;
  });

  it("prefers OpenAI when user has openai key", async () => {
    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    (getUserApiKey as unknown as Mock).mockImplementation(
      async (_uid: string, svc: string) => (svc === "openai" ? "sk-openai" : null)
    );
    const { resolveProvider } = await import("../registry");
    const result = await resolveProvider("user-1", "gpt-4o-mini");
    expect(result.provider).toBe("openai");
    expect(result.model).toContain("openai(");
    expect(result.headers).toBeUndefined();
    expect(result.modelId).toBe("gpt-4o-mini");
  });

  it("falls back to OpenRouter and attaches attribution headers", async () => {
    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    (getUserApiKey as unknown as Mock).mockImplementation(
      async (_uid: string, svc: string) => (svc === "openrouter" ? "sk-or" : null)
    );
    const { resolveProvider } = await import("../registry");
    const result = await resolveProvider(
      "user-2",
      "anthropic/claude-3.7-sonnet:thinking"
    );
    expect(result.provider).toBe("openrouter");
    expect(result.model).toContain("openai(https://openrouter.ai/api/v1)");
    expect(result.headers).toMatchObject({
      "HTTP-Referer": "https://example.com",
      "X-Title": "TripSage",
    });
    expect(result.modelId).toBe("anthropic/claude-3.7-sonnet:thinking");
  });

  it("falls back to OpenRouter and does not attach headers when envs unset", async () => {
    const env2 = {
      ...process.env,
    } as typeof process.env & {
      // biome-ignore lint/style/useNamingConvention: Environment variable names must match actual env vars
      OPENROUTER_REFERER?: string;
      // biome-ignore lint/style/useNamingConvention: Environment variable names must match actual env vars
      OPENROUTER_TITLE?: string;
    };
    env2.OPENROUTER_REFERER = undefined;
    env2.OPENROUTER_TITLE = undefined;
    process.env = env2;
    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    (getUserApiKey as unknown as Mock).mockImplementation(
      async (_uid: string, svc: string) => (svc === "openrouter" ? "sk-or" : null)
    );
    const { resolveProvider } = await import("../registry");
    const result = await resolveProvider("user-6", "openai/gpt-4o-mini");
    expect(result.provider).toBe("openrouter");
    expect(result.model).toContain("openai(https://openrouter.ai/api/v1)");
    expect(result.headers).toBeUndefined();
    // restore env for other tests
    process.env = env;
  });

  it("uses Anthropic when only anthropic key exists", async () => {
    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    (getUserApiKey as unknown as Mock).mockImplementation(
      async (_uid: string, svc: string) => (svc === "anthropic" ? "sk-ant" : null)
    );
    const { resolveProvider } = await import("../registry");
    const result = await resolveProvider("user-3", "claude-3-5-sonnet-20241022");
    expect(result.provider).toBe("anthropic");
    expect(result.model).toContain("anthropic::key::claude-3-5-sonnet-20241022");
    expect(result.headers).toBeUndefined();
  });

  it("uses xAI (OpenAI-compatible) when only xai key exists", async () => {
    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    (getUserApiKey as unknown as Mock).mockImplementation(
      async (_uid: string, svc: string) => (svc === "xai" ? "sk-xai" : null)
    );
    const { resolveProvider } = await import("../registry");
    const result = await resolveProvider("user-4", "grok-3");
    expect(result.provider).toBe("xai");
    expect(result.model).toContain("x.ai/v1");
    expect(result.headers).toBeUndefined();
  });

  it("throws when user has no provider keys", async () => {
    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    (getUserApiKey as unknown as Mock).mockResolvedValue(null);
    const { resolveProvider } = await import("../registry");
    await expect(resolveProvider("user-5")).rejects.toThrow(/No provider key found/);
  });
});
