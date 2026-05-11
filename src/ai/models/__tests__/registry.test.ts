/** @vitest-environment node */

import {
  ANTHROPIC_VALIDATION_MODEL_ID,
  DEFAULT_GATEWAY_MODEL_ID,
  DEFAULT_OPENAI_MODEL_ID,
  DEFAULT_OPENROUTER_MODEL_ID,
  DEFAULT_XAI_MODEL_ID,
} from "@ai/models/defaults";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const makeModel = (label: string) => {
  const fn = vi.fn();
  fn.toString = () => label;
  return fn;
};

const LOGGER_WARN = vi.hoisted(() => vi.fn());

vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: () => ({
    error: vi.fn(),
    info: vi.fn(),
    warn: LOGGER_WARN,
  }),
}));

vi.mock("@/lib/supabase/rpc", () => ({
  getUserAllowGatewayFallback: vi.fn(async () => true),
  getUserApiKey: vi.fn(),
  getUserGatewayBaseUrl: vi.fn(async () => null),
  touchUserApiKey: vi.fn(async () => undefined),
}));

// Mock provider factories to return simple tagged model ids for assertions.
vi.mock("@ai-sdk/openai", () => ({
  createOpenAI: (opts: { apiKey?: string; baseURL?: string }) => ({
    chat: (id: string) =>
      makeModel(
        `openai-chat(${opts.baseURL ?? "api.openai.com"})::${opts.apiKey ? "key" : "no-key"}::${id}`
      ),
    responses: (id: string) =>
      makeModel(
        `openai-responses(${opts.baseURL ?? "api.openai.com"})::${opts.apiKey ? "key" : "no-key"}::${id}`
      ),
  }),
}));

vi.mock("@ai-sdk/anthropic", () => ({
  anthropic: (id: string) => makeModel(`anthropic::${id}`),
  createAnthropic: (opts: { apiKey?: string }) => (id: string) =>
    makeModel(`anthropic::${opts.apiKey ? "key" : "no-key"}::${id}`),
}));

// OpenRouter now uses OpenAI-compatible provider with baseURL pointing to OpenRouter.

vi.mock("ai", () => ({
  createGateway: (opts: { apiKey?: string; baseURL?: string }) => (id: string) =>
    makeModel(
      `gateway(${opts.baseURL ?? "https://ai-gateway.vercel.sh/v3/ai"})::${opts.apiKey ? "key" : "no-key"}::${id}`
    ),
}));

vi.mock("@ai-sdk/xai", () => ({
  createXai: (opts: { apiKey?: string }) => (id: string) =>
    makeModel(`xai::${opts.apiKey ? "key" : "no-key"}::${id}`),
}));

describe("resolveProvider", () => {
  const env = process.env;
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
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
    vi.mocked(getUserApiKey).mockImplementation(async (_uid: string, svc: string) =>
      svc === "openai" ? "sk-openai" : null
    );
    const { resolveProvider } = await import("@ai/models/registry");
    const result = await resolveProvider("user-1");
    expect(result.provider).toBe("openai");
    expect(String(result.model)).toContain("openai-responses(");
    expect(result.modelId).toBe(DEFAULT_OPENAI_MODEL_ID);
  });

  it("uses per-user Gateway when gateway key exists", async () => {
    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    vi.mocked(getUserApiKey).mockImplementation(async (_uid: string, svc: string) =>
      svc === "gateway" ? "gw-user-key" : null
    );
    const { resolveProvider } = await import("@ai/models/registry");
    const result = await resolveProvider("user-gw", DEFAULT_GATEWAY_MODEL_ID);
    expect(result.provider).toBe("openai");
    expect(String(result.model)).toContain(
      `gateway(https://ai-gateway.vercel.sh/v3/ai)::key::${DEFAULT_GATEWAY_MODEL_ID}`
    );
  });

  it("normalizes unprefixed model ids for Gateway usage", async () => {
    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    vi.mocked(getUserApiKey).mockImplementation(async (_uid: string, svc: string) =>
      svc === "gateway" ? "gw-user-key" : null
    );
    const { resolveProvider } = await import("@ai/models/registry");
    const result = await resolveProvider("user-gw2", DEFAULT_OPENAI_MODEL_ID);
    expect(result.provider).toBe("openai");
    expect(result.modelId).toBe(DEFAULT_GATEWAY_MODEL_ID);
    expect(String(result.model)).toContain(
      `gateway(https://ai-gateway.vercel.sh/v3/ai)::key::${DEFAULT_GATEWAY_MODEL_ID}`
    );
  });

  it("fails closed when a configured user Gateway base URL is invalid", async () => {
    const { getUserApiKey, getUserGatewayBaseUrl } = await import("@/lib/supabase/rpc");
    vi.mocked(getUserApiKey).mockImplementation((_uid: string, svc: string) => {
      if (svc === "gateway") return Promise.resolve("gw-user-key");
      if (svc === "openai") return Promise.resolve("sk-openai");
      return Promise.resolve(null);
    });
    vi.mocked(getUserGatewayBaseUrl).mockResolvedValue(
      "https://unexpected.example.com/v1"
    );

    const { resolveProvider } = await import("@ai/models/registry");
    await expect(resolveProvider("user-stale-gw")).rejects.toThrow(
      /Gateway base URL rejected: host_not_allowed/
    );
    expect(LOGGER_WARN).toHaveBeenCalledWith(
      "gateway_base_url_rejected",
      expect.objectContaining({
        reason: "host_not_allowed",
        source: "user",
      })
    );
  });

  it("falls back to OpenRouter", async () => {
    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    vi.mocked(getUserApiKey).mockImplementation(async (_uid: string, svc: string) =>
      svc === "openrouter" ? "sk-or" : null
    );
    const { resolveProvider } = await import("@ai/models/registry");
    const result = await resolveProvider("user-2", "anthropic/claude-sonnet-4.6");
    expect(result.provider).toBe("openrouter");
    // The OpenRouter path uses OpenAI provider with baseURL set to openrouter.
    expect(String(result.model)).toContain(
      "openai-chat(https://openrouter.ai/api/v1)::key::anthropic/claude-sonnet-4.6"
    );
    expect(result.modelId).toBe("anthropic/claude-sonnet-4.6");
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
    vi.mocked(getUserApiKey).mockImplementation(async (_uid: string, svc: string) =>
      svc === "openrouter" ? "sk-or" : null
    );
    const { resolveProvider } = await import("@ai/models/registry");
    const result = await resolveProvider("user-6");
    expect(result.provider).toBe("openrouter");
    expect(String(result.model)).toContain(
      `openai-chat(https://openrouter.ai/api/v1)::key::${DEFAULT_OPENROUTER_MODEL_ID}`
    );
    expect(result.modelId).toBe(DEFAULT_OPENROUTER_MODEL_ID);
    // restore env for other tests
    process.env = env;
  });

  it("requires an explicit model when only anthropic key exists", async () => {
    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    vi.mocked(getUserApiKey).mockImplementation(async (_uid: string, svc: string) =>
      svc === "anthropic" ? "sk-ant" : null
    );
    const { resolveProvider } = await import("@ai/models/registry");

    await expect(resolveProvider("user-3")).rejects.toThrow(
      /model must be selected explicitly for anthropic/
    );
  });

  it("uses Anthropic with an explicit current model", async () => {
    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    vi.mocked(getUserApiKey).mockImplementation(async (_uid: string, svc: string) =>
      svc === "anthropic" ? "sk-ant" : null
    );
    const { resolveProvider } = await import("@ai/models/registry");
    const result = await resolveProvider(
      "user-3",
      `anthropic/${ANTHROPIC_VALIDATION_MODEL_ID}`
    );

    expect(result.provider).toBe("anthropic");
    expect(String(result.model)).toContain(
      `anthropic::key::${ANTHROPIC_VALIDATION_MODEL_ID}`
    );
    expect(result.modelId).toBe(ANTHROPIC_VALIDATION_MODEL_ID);
  });

  it("rejects foreign provider-qualified hints for direct BYOK providers", async () => {
    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    vi.mocked(getUserApiKey).mockImplementation(async (_uid: string, svc: string) =>
      svc === "anthropic" ? "sk-ant" : null
    );
    const { resolveProvider } = await import("@ai/models/registry");

    await expect(
      resolveProvider("user-foreign-hint", "openai/gpt-5.5")
    ).rejects.toThrow(/targets a different provider/);
  });

  it("uses xAI when only xai key exists", async () => {
    const { getUserApiKey } = await import("@/lib/supabase/rpc");
    vi.mocked(getUserApiKey).mockImplementation(async (_uid: string, svc: string) =>
      svc === "xai" ? "sk-xai" : null
    );
    const { resolveProvider } = await import("@ai/models/registry");
    const result = await resolveProvider("user-4");
    expect(result.provider).toBe("xai");
    expect(String(result.model)).toContain(`xai::key::${DEFAULT_XAI_MODEL_ID}`);
    expect(result.modelId).toBe(DEFAULT_XAI_MODEL_ID);
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
    vi.mocked(getUserApiKey).mockResolvedValue(null);
    const { resolveProvider } = await import("@ai/models/registry");

    await expect(resolveProvider("user-5")).rejects.toThrow(/No provider key found/);

    // Restore original environment
    process.env = originalEnv;
  });

  it("logs BYOK lookup failures without raw RPC messages", async () => {
    const originalEnv = process.env;
    process.env = {
      ...process.env,
      AI_GATEWAY_API_KEY: undefined,
      ANTHROPIC_API_KEY: undefined,
      OPENAI_API_KEY: undefined,
      OPENROUTER_API_KEY: undefined,
      XAI_API_KEY: undefined,
    };

    try {
      const { getUserApiKey } = await import("@/lib/supabase/rpc");
      vi.mocked(getUserApiKey).mockImplementation((_uid: string, svc: string) => {
        if (svc === "openai") {
          return Promise.reject(new Error("secret leaked"));
        }
        return Promise.resolve(null);
      });
      const { resolveProvider } = await import("@ai/models/registry");

      await expect(resolveProvider("user-log")).rejects.toThrow(
        /OpenAI BYOK lookup failed/
      );

      expect(LOGGER_WARN).toHaveBeenCalledWith(
        "byok_lookup_failed",
        expect.objectContaining({
          errorName: "Error",
          provider: "openai",
        })
      );
      expect(JSON.stringify(LOGGER_WARN.mock.calls)).not.toContain("secret leaked");
    } finally {
      process.env = originalEnv;
    }
  });

  it("does not use team Gateway when OpenAI BYOK lookup fails", async () => {
    const originalEnv = process.env;
    process.env = {
      ...process.env,
      AI_GATEWAY_API_KEY: "aaaaaaaaaaaaaaaaaaaa",
      ANTHROPIC_API_KEY: undefined,
      NEXT_PUBLIC_SUPABASE_ANON_KEY: "anon",
      NEXT_PUBLIC_SUPABASE_URL: "https://example.supabase.co",
      OPENAI_API_KEY: undefined,
      OPENROUTER_API_KEY: undefined,
      XAI_API_KEY: undefined,
    };

    try {
      const { getUserAllowGatewayFallback, getUserApiKey } = await import(
        "@/lib/supabase/rpc"
      );
      const { resolveProvider } = await import("@ai/models/registry");

      vi.mocked(getUserAllowGatewayFallback).mockResolvedValue(true);
      vi.mocked(getUserApiKey).mockImplementation((_uid: string, svc: string) => {
        if (svc === "openai") {
          return Promise.reject(new Error("secret leaked"));
        }
        return Promise.resolve(null);
      });

      await expect(resolveProvider("user-openai-fail")).rejects.toThrow(
        /OpenAI BYOK lookup failed/
      );
    } finally {
      process.env = originalEnv;
    }
  });

  it("falls back to team Gateway when configured and user has no keys", async () => {
    const originalEnv = process.env;
    process.env = {
      ...process.env,
      AI_GATEWAY_API_KEY: "aaaaaaaaaaaaaaaaaaaa",
      ANTHROPIC_API_KEY: undefined,
      // Minimal required vars so server env parsing doesn't fail.
      NEXT_PUBLIC_SUPABASE_ANON_KEY: "anon",
      NEXT_PUBLIC_SUPABASE_URL: "https://example.supabase.co",
      OPENAI_API_KEY: undefined,
      OPENROUTER_API_KEY: undefined,
      XAI_API_KEY: undefined,
    };

    try {
      const { getUserAllowGatewayFallback, getUserApiKey } = await import(
        "@/lib/supabase/rpc"
      );
      const { resolveProvider } = await import("@ai/models/registry");

      vi.mocked(getUserAllowGatewayFallback).mockResolvedValue(true);
      vi.mocked(getUserApiKey).mockResolvedValue(null);

      const result = await resolveProvider("user-bypass");

      expect(vi.mocked(getUserApiKey)).toHaveBeenCalled();
      expect(vi.mocked(getUserAllowGatewayFallback)).toHaveBeenCalled();
      expect(result.provider).toBe("openai");
      expect(String(result.model)).toContain("gateway(");
      expect(result.modelId).toBe(DEFAULT_GATEWAY_MODEL_ID);
    } finally {
      process.env = originalEnv;
    }
  });

  it("uses server provider keys when user disables team Gateway fallback", async () => {
    const originalEnv = process.env;
    process.env = {
      ...process.env,
      AI_GATEWAY_API_KEY: "aaaaaaaaaaaaaaaaaaaa",
      ANTHROPIC_API_KEY: undefined,
      // Minimal required vars so server env parsing doesn't fail.
      NEXT_PUBLIC_SUPABASE_ANON_KEY: "anon",
      NEXT_PUBLIC_SUPABASE_URL: "https://example.supabase.co",
      OPENAI_API_KEY: undefined,
      OPENROUTER_API_KEY: undefined,
      XAI_API_KEY: "aaaaaaaaaaaaaaaaaaaa",
    };

    try {
      const { getUserAllowGatewayFallback, getUserApiKey } = await import(
        "@/lib/supabase/rpc"
      );
      const { resolveProvider } = await import("@ai/models/registry");

      vi.mocked(getUserAllowGatewayFallback).mockResolvedValue(false);
      vi.mocked(getUserApiKey).mockResolvedValue(null);

      const result = await resolveProvider("user-server-provider");

      expect(result.provider).toBe("xai");
      expect(result.credentialSource).toBe("server-provider");
      expect(String(result.model)).toContain(`xai::key::${DEFAULT_XAI_MODEL_ID}`);
    } finally {
      process.env = originalEnv;
    }
  });

  it("reports no eligible provider when user disables Gateway fallback and no server keys exist", async () => {
    const originalEnv = process.env;
    process.env = {
      ...process.env,
      AI_GATEWAY_API_KEY: "aaaaaaaaaaaaaaaaaaaa",
      ANTHROPIC_API_KEY: undefined,
      // Minimal required vars so server env parsing doesn't fail.
      NEXT_PUBLIC_SUPABASE_ANON_KEY: "anon",
      NEXT_PUBLIC_SUPABASE_URL: "https://example.supabase.co",
      OPENAI_API_KEY: undefined,
      OPENROUTER_API_KEY: undefined,
      XAI_API_KEY: undefined,
    };

    try {
      const { getUserAllowGatewayFallback, getUserApiKey } = await import(
        "@/lib/supabase/rpc"
      );
      const { resolveProvider } = await import("@ai/models/registry");

      vi.mocked(getUserAllowGatewayFallback).mockResolvedValue(false);
      vi.mocked(getUserApiKey).mockResolvedValue(null);

      await expect(resolveProvider("user-no-fallback")).rejects.toThrow(
        /Team Gateway fallback was skipped because disabled/
      );
    } finally {
      process.env = originalEnv;
    }
  });
});
