/**
 * @fileoverview Modernized tests for the API key Zustand store.
 */

import { act, renderHook } from "@testing-library/react";
import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useApiKeyStore } from "@/stores/api-key-store";
import { createMockSupabaseClient } from "@/test/mock-helpers";
import type { ApiKey } from "@/types/api-keys";

let supabase = createMockSupabaseClient();
let fetchApiMock: Mock = vi.fn();

vi.mock("@/lib/api/client", () => ({
  fetchApi: (...args: unknown[]) => fetchApiMock(...args),
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => supabase,
  getBrowserClient: () => supabase,
  useSupabase: () => supabase,
}));

const getDefaultKeys = (): Record<string, ApiKey> => ({
  openai: {
    id: "key-1",
    service: "openai",
    has_key: true,
    is_valid: true,
    last_validated: "2025-01-01T00:00:00Z",
    last_used: "2025-01-05T00:00:00Z",
  },
});

describe("useApiKeyStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    supabase = createMockSupabaseClient();
    fetchApiMock = vi.fn();

    (supabase.auth.getSession as Mock).mockResolvedValue({
      data: { session: null },
      error: null,
    });

    act(() => {
      useApiKeyStore.setState({
        isAuthenticated: false,
        userId: null,
        token: null,
        isApiKeyValid: false,
        authError: null,
        supportedServices: [],
        keys: {},
        selectedService: null,
      });
    });
  });

  it("exposes the initial state", () => {
    const { result } = renderHook(() => useApiKeyStore());
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.userId).toBeNull();
    expect(result.current.keys).toEqual({});
    expect(result.current.supportedServices).toEqual([]);
    expect(result.current.isApiKeyValid).toBe(false);
    expect(result.current.authError).toBeNull();
  });

  it("loads API keys when a session exists", async () => {
    (supabase.auth.getSession as Mock).mockResolvedValue({
      data: { session: { access_token: "token-123" } },
      error: null,
    });

    fetchApiMock.mockResolvedValue({
      keys: getDefaultKeys(),
      supported_services: ["openai", "anthropic"],
    });

    const { result } = renderHook(() => useApiKeyStore());

    await act(async () => {
      await result.current.loadKeys();
    });

    expect(fetchApiMock).toHaveBeenCalledWith("/api/keys", {
      auth: "Bearer token-123",
    });
    expect(result.current.keys.openai?.service).toBe("openai");
    expect(result.current.supportedServices).toEqual(["openai", "anthropic"]);
    expect(result.current.authError).toBeNull();
  });

  it("sets authentication state and clears errors", () => {
    const { result } = renderHook(() => useApiKeyStore());

    act(() => {
      result.current.setAuthError("failure");
      result.current.setAuthenticated(true, "user-123", "token-123");
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.userId).toBe("user-123");
    expect(result.current.token).toBe("token-123");
    expect(result.current.authError).toBeNull();
  });

  it("validates API keys via the API client", async () => {
    (supabase.auth.getSession as Mock).mockResolvedValue({
      data: { session: { access_token: "token-456" } },
      error: null,
    });

    fetchApiMock.mockResolvedValueOnce({
      is_valid: true,
      message: null,
    });

    const { result } = renderHook(() => useApiKeyStore());

    act(() => {
      result.current.setKeys(getDefaultKeys());
    });

    const isValid = await result.current.validateKey("openai", "secret");

    expect(fetchApiMock).toHaveBeenCalledWith("/api/keys/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      auth: "Bearer token-456",
      body: JSON.stringify({
        service: "openai",
        api_key: "secret",
        save: false,
      }),
    });

    expect(isValid).toBe(true);
    expect(result.current.isApiKeyValid).toBe(true);
    expect(result.current.authError).toBeNull();
  });

  it("returns false when validation fails", async () => {
    (supabase.auth.getSession as Mock).mockResolvedValue({
      data: { session: { access_token: "token-789" } },
      error: null,
    });

    fetchApiMock.mockResolvedValueOnce({
      is_valid: false,
      message: "Invalid key",
    });

    const { result } = renderHook(() => useApiKeyStore());

    act(() => {
      result.current.setKeys(getDefaultKeys());
    });

    const isValid = await result.current.validateKey("openai", "secret");

    expect(isValid).toBe(false);
    expect(result.current.isApiKeyValid).toBe(false);
    expect(result.current.authError).toBe("Invalid key");
  });

  it("returns false when key is missing", async () => {
    const { result } = renderHook(() => useApiKeyStore());

    const isValid = await result.current.validateKey("openai", undefined);

    expect(isValid).toBe(false);
    expect(result.current.authError).toBe("No API key found for openai");
  });

  it("logout resets authentication-sensitive state", () => {
    const { result } = renderHook(() => useApiKeyStore());

    act(() => {
      result.current.setAuthenticated(true, "user", "token");
      result.current.setKeys(getDefaultKeys());
      result.current.setSelectedService("openai");
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.userId).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.keys).toEqual({});
    expect(result.current.selectedService).toBeNull();
  });
});
