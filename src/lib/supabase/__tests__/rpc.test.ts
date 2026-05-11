/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TypedAdminSupabase } from "@/lib/supabase/admin";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { createMockSupabaseClient, getSupabaseMockState } from "@/test/mocks/supabase";

vi.mock("server-only", () => ({}));

const MOCK_SPAN = vi.hoisted(() => ({
  setAttribute: vi.fn(),
}));
const MOCK_WITH_TELEMETRY_SPAN = vi.hoisted(() =>
  vi.fn(
    (_name: string, _options: unknown, execute: (span: typeof MOCK_SPAN) => unknown) =>
      execute(MOCK_SPAN)
  )
);

vi.mock("@/lib/telemetry/identifiers", () => ({
  hashTelemetryIdentifier: vi.fn((identifier: string) => `hash:${identifier}`),
}));

vi.mock("@/lib/telemetry/span", () => ({
  recordErrorOnSpan: vi.fn((span: typeof MOCK_SPAN, error: Error) => {
    span.setAttribute("recorded.error", error.message);
  }),
  withTelemetrySpan: MOCK_WITH_TELEMETRY_SPAN,
}));

describe("rpc helpers", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("calls insert_user_api_key with normalized service", async () => {
    const mockClient = createMockSupabaseClient();
    const rpcSpy = vi.spyOn(mockClient, "rpc");
    const { insertUserApiKey } = await import("../rpc");
    await insertUserApiKey("user-1", "OpenAI", "sk-test", mockClient);
    expect(rpcSpy).toHaveBeenCalledWith("insert_user_api_key", {
      p_api_key: "sk-test",
      p_service: "openai",
      p_user_id: "user-1",
    });
    expect(MOCK_WITH_TELEMETRY_SPAN).toHaveBeenCalledWith(
      "supabase.rpc.insert_user_api_key",
      {
        attributes: expect.objectContaining({
          "keys.operation": "insert",
          "keys.service": "openai",
          "keys.user_id_hash": "hash:user-1",
          "rpc.name": "insert_user_api_key",
        }),
      },
      expect.any(Function)
    );
    expect(MOCK_SPAN.setAttribute).toHaveBeenCalledWith("rpc.error", false);
  });

  it("calls delete_user_api_key with normalized service", async () => {
    const mockClient = createMockSupabaseClient();
    const rpcSpy = vi.spyOn(mockClient, "rpc");
    const { deleteUserApiKey } = await import("../rpc");
    await deleteUserApiKey("user-1", "xai", mockClient);
    expect(rpcSpy).toHaveBeenCalledWith("delete_user_api_key", {
      p_service: "xai",
      p_user_id: "user-1",
    });
  });

  it("returns value from get_user_api_key", async () => {
    const mockClient = createMockSupabaseClient();
    getSupabaseMockState(mockClient).rpcResults.set("get_user_api_key", {
      data: "secret",
      error: null,
    });
    const { getUserApiKey } = await import("../rpc");
    const res = await getUserApiKey("user-1", "openrouter", mockClient);
    expect(res).toBe("secret");
  });

  it("checks BYOK vault health without returning secret data", async () => {
    const mockClient = createMockSupabaseClient();
    getSupabaseMockState(mockClient).rpcResults.set("check_byok_vault_health", {
      data: true,
      error: null,
    });
    const rpcSpy = vi.spyOn(mockClient, "rpc");
    const { checkByokVaultHealth } = await import("../rpc");

    await checkByokVaultHealth(mockClient);

    expect(rpcSpy).toHaveBeenCalledWith("check_byok_vault_health");
    expect(MOCK_WITH_TELEMETRY_SPAN).toHaveBeenCalledWith(
      "supabase.rpc.check_byok_vault_health",
      {
        attributes: expect.objectContaining({
          "keys.operation": "health",
          "keys.service": "vault",
          "rpc.name": "check_byok_vault_health",
        }),
      },
      expect.any(Function)
    );
  });

  it("throws when BYOK vault health returns an unexpected result", async () => {
    const mockClient = createMockSupabaseClient();
    getSupabaseMockState(mockClient).rpcResults.set("check_byok_vault_health", {
      data: false,
      error: null,
    });
    const { checkByokVaultHealth } = await import("../rpc");

    await expect(checkByokVaultHealth(mockClient)).rejects.toThrow(
      "BYOK Vault health RPC returned an unexpected result"
    );
    expect(MOCK_SPAN.setAttribute).toHaveBeenCalledWith("rpc.error", true);
  });

  it("preserves structured Supabase RPC error metadata", async () => {
    const mockClient = unsafeCast<TypedAdminSupabase>({
      rpc: vi.fn(async () => ({
        data: null,
        error: {
          code: "PGRST301",
          details: "vault schema unavailable",
          hint: "check extension",
          message: "Vault unavailable",
        },
      })),
    });
    const { checkByokVaultHealth } = await import("../rpc");

    await expect(checkByokVaultHealth(mockClient)).rejects.toMatchObject({
      code: "PGRST301",
      details: "vault schema unavailable",
      hint: "check extension",
      message: "Vault unavailable",
    });
  });

  it("throws on invalid service", async () => {
    const { insertUserApiKey } = await import("../rpc");
    await expect(insertUserApiKey("u", "bad", "k")).rejects.toThrow("Invalid service");
  });
});
