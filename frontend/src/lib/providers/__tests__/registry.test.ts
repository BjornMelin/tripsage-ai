import { afterEach, beforeEach, describe, expect, it, type Mock, vi } from "vitest";

vi.mock("@/lib/supabase/rpc", () => ({
  getUserAllowGatewayFallback: vi.fn(async () => true),
  getUserApiKey: vi.fn(),
  getUserGatewayBaseUrl: vi.fn(async () => null),
  touchUserApiKey: vi.fn(async () => undefined),
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

// OpenRouter now uses OpenAI-compatible provider with baseURL pointing to OpenRouter.

vi.mock("ai", () => ({
  createGateway: (opts: { apiKey?: string; baseURL?: string }) => (id: string) =>
    `gateway(${opts.baseURL ?? "https://ai-gateway.vercel.sh/v1"})::${opts.apiKey ? "key" : "no-key"}::${id}`,
}));

vi.mock("@ai-sdk/xai", () => ({
  createXai: (opts: { apiKey?: string }) => (id: string) =>
    `xai::${opts.apiKey ? "key" : "no-key"}::${id}`,
}));

describe("resolveProvider", () => {
  const env = process.env;
  beforeEach(() => {
    vi.resetModules();
    process.env = {
      ...env,
      NEXT_PUBLIC_APP_NAME: "TripSage",
      NEXT_PUBLIC_SITE_URL: "https://example.com",
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
    const { resolveProvider } = await import("@ai/models/registry");
    const result = await resolveProvider("user-1", "gpt-4o-mini");
    expect(result.provider).toBe("openai");
    expect(result.model).toContain("openai(");
    expect(result.modelId).toBe("gpt-4o-mini");
  });

  it("uses per-user Gateway when gateway key exists", async () => {
    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    (getUserApiKey as unknown as Mock).mockImplementation(
      async (_uid: string, svc: string) => (svc === "gateway" ? "gw-user-key" : null)
    );
    const { resolveProvider } = await import("@ai/models/registry");
    const result = await resolveProvider("user-gw", "openai/gpt-4o-mini");
    expect(result.provider).toBe("openai");
    expect(String(result.model)).toContain(
      "gateway(https://ai-gateway.vercel.sh/v1)::key::openai/gpt-4o-mini"
    );
  });

  it("falls back to OpenRouter", async () => {
    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    (getUserApiKey as unknown as Mock).mockImplementation(
      async (_uid: string, svc: string) => (svc === "openrouter" ? "sk-or" : null)
    );
    const { resolveProvider } = await import("@ai/models/registry");
    const result = await resolveProvider(
      "user-2",
      "anthropic/claude-3.7-sonnet:thinking"
    );
    expect(result.provider).toBe("openrouter");
    // The OpenRouter path uses OpenAI provider with baseURL set to openrouter.
    expect(String(result.model)).toContain(
      "openai(https://openrouter.ai/api/v1)::key::anthropic/claude-3.7-sonnet:thinking"
    );
    expect(result.modelId).toBe("anthropic/claude-3.7-sonnet:thinking");
  });

  it("falls back to OpenRouter when envs unset", async () => {
    const env2 = {
      ...process.env,
    } as typeof process.env & {
      // biome-ignore lint/style/useNamingConvention: Environment variable names must match actual env vars
      NEXT_PUBLIC_SITE_URL?: string;
      // biome-ignore lint/style/useNamingConvention: Environment variable names must match actual env vars
      NEXT_PUBLIC_APP_NAME?: string;
    };
    env2.NEXT_PUBLIC_SITE_URL = undefined;
    env2.NEXT_PUBLIC_APP_NAME = undefined;
    process.env = env2;
    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    (getUserApiKey as unknown as Mock).mockImplementation(
      async (_uid: string, svc: string) => (svc === "openrouter" ? "sk-or" : null)
    );
    const { resolveProvider } = await import("@ai/models/registry");
    const result = await resolveProvider("user-6", "openai/gpt-4o-mini");
    expect(result.provider).toBe("openrouter");
    expect(String(result.model)).toContain(
      "openai(https://openrouter.ai/api/v1)::key::openai/gpt-4o-mini"
    );
    // restore env for other tests
    process.env = env;
  });

  it("uses Anthropic when only anthropic key exists", async () => {
    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    (getUserApiKey as unknown as Mock).mockImplementation(
      async (_uid: string, svc: string) => (svc === "anthropic" ? "sk-ant" : null)
    );
    const { resolveProvider } = await import("@ai/models/registry");
    const result = await resolveProvider("user-3", "claude-3-5-sonnet-20241022");
    expect(result.provider).toBe("anthropic");
    expect(result.model).toContain("anthropic::key::claude-3-5-sonnet-20241022");
  });

  it("uses xAI when only xai key exists", async () => {
    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    (getUserApiKey as unknown as Mock).mockImplementation(
      async (_uid: string, svc: string) => (svc === "xai" ? "sk-xai" : null)
    );
    const { resolveProvider } = await import("@ai/models/registry");
    const result = await resolveProvider("user-4", "grok-3");
    expect(result.provider).toBe("xai");
    expect(String(result.model)).toContain("xai::key::grok-3");
  });

  it("throws when user has no provider keys", async () => {
    // Clear all API keys from environment to test the error path
    const originalEnv = process.env;
    process.env = {
      ...process.env,
      AI_GATEWAY_API_KEY: undefined,
      ANTHROPIC_API_KEY: undefined,
      OPENAI_API_KEY: undefined,
      OPENROUTER_API_KEY: undefined,
      XAI_API_KEY: undefined,
    };

    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    (getUserApiKey as unknown as Mock).mockResolvedValue(null);
    const { resolveProvider } = await import("@ai/models/registry");

    await expect(resolveProvider("user-5")).rejects.toThrow(/No provider key found/);

    // Restore original environment
    process.env = originalEnv;
  });
});
