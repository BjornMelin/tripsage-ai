import { beforeEach, describe, expect, it, vi } from "vitest";

type SpanCapture = { attrs: Record<string, unknown> | undefined; name: string };
const CAPTURED: SpanCapture[] = [];

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: vi.fn(),
  sanitizeAttributes: (attrs: Record<string, unknown>) => attrs,
  withTelemetrySpan: async (
    name: string,
    options: { attributes?: Record<string, unknown> },
    execute: (span: unknown) => unknown
  ) => {
    CAPTURED.push({ attrs: options?.attributes, name });
    const _unused = {};
    return await execute(_unused);
  },
}));

vi.mock("@/lib/supabase/rpc", () => ({
  getUserAllowGatewayFallback: vi.fn(async () => true),
  getUserApiKey: vi.fn(async (_uid: string, svc: string) =>
    svc === "gateway" ? "gw-user-key" : null
  ),
  getUserGatewayBaseUrl: vi.fn(async () => "https://gw.example.com/v1"),
  touchUserApiKey: vi.fn(async () => undefined),
}));

vi.mock("ai", () => ({
  createGateway: (opts: { apiKey?: string; baseURL?: string }) => (id: string) => ({
    baseURL: opts.baseURL ?? "https://ai-gateway.vercel.sh/v1",
    id,
    kind: "gateway-mock",
    withKey: Boolean(opts.apiKey),
  }),
}));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVar: (key: string) => process.env[key] || "",
  getServerEnvVarWithFallback: (key: string, fallback?: string) => {
    if (key === "AI_GATEWAY_API_KEY") return "team-key";
    if (key === "AI_GATEWAY_URL") return "https://ai-gateway.vercel.sh/v1";
    return fallback as string | undefined;
  },
}));

describe("resolveProvider telemetry", () => {
  beforeEach(() => {
    CAPTURED.length = 0;
    vi.resetModules();
  });

  it("emits attributes for user-gateway path", async () => {
    const { resolveProvider } = await import("@ai/models/registry");
    await resolveProvider("u1", "openai/gpt-4o-mini");
    const span = CAPTURED.find((c) => c.name === "providers.resolve");
    expect(span?.attrs).toMatchObject({
      baseUrlHost: "gw.example.com",
      baseUrlSource: "user",
      path: "user-gateway",
      provider: "gateway",
    });
  });

  it("emits attributes for team-gateway path", async () => {
    // No user gateway; enable team fallback via env key
    const rpc = await import("@/lib/supabase/rpc");
    (
      rpc as unknown as { getUserApiKey: (a?: unknown, b?: unknown) => unknown }
    ).getUserApiKey = vi.fn(async () => null);
    vi.stubEnv("AI_GATEWAY_API_KEY", "team-key");
    vi.stubEnv("AI_GATEWAY_URL", "https://ai-gateway.vercel.sh/v1");
    const { resolveProvider } = await import("@ai/models/registry");
    await resolveProvider("u2", "openai/gpt-4o-mini");
    const span = CAPTURED.filter((c) => c.name === "providers.resolve").pop();
    expect(span?.attrs).toMatchObject({
      baseUrlHost: "ai-gateway.vercel.sh",
      baseUrlSource: "team",
      path: "team-gateway",
      provider: "gateway",
    });
  });
});
