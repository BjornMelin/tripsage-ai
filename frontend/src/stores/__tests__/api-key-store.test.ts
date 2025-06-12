import type { ApiKey } from "@/types/api-keys";
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useApiKeyStore } from "../api-key-store";

// Mock fetch globally
global.fetch = vi.fn();

describe("API Key Store", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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

  describe("Initial State", () => {
    it("initializes with correct default values", () => {
      const { result } = renderHook(() => useApiKeyStore());

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.userId).toBeNull();
      expect(result.current.token).toBeNull();
      expect(result.current.isApiKeyValid).toBe(false);
      expect(result.current.authError).toBeNull();
      expect(result.current.supportedServices).toEqual([]);
      expect(result.current.keys).toEqual({});
      expect(result.current.selectedService).toBeNull();
    });
  });

  describe("Authentication Management", () => {
    it("sets authenticated state correctly", () => {
      const { result } = renderHook(() => useApiKeyStore());

      act(() => {
        result.current.setAuthenticated(true, "user-123", "mock-token");
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.userId).toBe("user-123");
      expect(result.current.token).toBe("mock-token");
      expect(result.current.authError).toBeNull();
    });

    it("sets authenticated state without optional parameters", () => {
      const { result } = renderHook(() => useApiKeyStore());

      act(() => {
        result.current.setAuthenticated(true);
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.userId).toBeNull();
      expect(result.current.token).toBeNull();
    });

    it("sets API key validity", () => {
      const { result } = renderHook(() => useApiKeyStore());

      expect(result.current.isApiKeyValid).toBe(false);

      act(() => {
        result.current.setApiKeyValid(true);
      });

      expect(result.current.isApiKeyValid).toBe(true);

      act(() => {
        result.current.setApiKeyValid(false);
      });

      expect(result.current.isApiKeyValid).toBe(false);
    });

    it("sets authentication error", () => {
      const { result } = renderHook(() => useApiKeyStore());

      expect(result.current.authError).toBeNull();

      act(() => {
        result.current.setAuthError("Authentication failed");
      });

      expect(result.current.authError).toBe("Authentication failed");

      act(() => {
        result.current.setAuthError(null);
      });

      expect(result.current.authError).toBeNull();
    });

    it("logs out user and clears all data", () => {
      const { result } = renderHook(() => useApiKeyStore());

      // Set up some state first
      act(() => {
        result.current.setAuthenticated(true, "user-123", "mock-token");
        result.current.setApiKeyValid(true);
        result.current.setKeys({
          openai: {
            id: "key-1",
            service: "openai",
            has_key: true,
            is_valid: true,
            last_validated: new Date().toISOString(),
            last_used: new Date().toISOString(),
          },
        });
        result.current.setSelectedService("openai");
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.keys).not.toEqual({});

      act(() => {
        result.current.logout();
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.userId).toBeNull();
      expect(result.current.token).toBeNull();
      expect(result.current.isApiKeyValid).toBe(false);
      expect(result.current.authError).toBeNull();
      expect(result.current.keys).toEqual({});
      expect(result.current.selectedService).toBeNull();
    });
  });

  describe("Service Management", () => {
    it("sets supported services", () => {
      const { result } = renderHook(() => useApiKeyStore());

      const services = ["openai", "anthropic", "google"];

      act(() => {
        result.current.setSupportedServices(services);
      });

      expect(result.current.supportedServices).toEqual(services);
    });

    it("sets selected service", () => {
      const { result } = renderHook(() => useApiKeyStore());

      expect(result.current.selectedService).toBeNull();

      act(() => {
        result.current.setSelectedService("openai");
      });

      expect(result.current.selectedService).toBe("openai");

      act(() => {
        result.current.setSelectedService(null);
      });

      expect(result.current.selectedService).toBeNull();
    });
  });

  describe("API Key Management", () => {
    it("sets keys correctly", () => {
      const { result } = renderHook(() => useApiKeyStore());

      const mockKeys: Record<string, ApiKey> = {
        openai: {
          id: "key-1",
          service: "openai",
          has_key: true,
          is_valid: true,
          last_validated: new Date().toISOString(),
          last_used: new Date().toISOString(),
        },
        anthropic: {
          id: "key-2",
          service: "anthropic",
          has_key: true,
          is_valid: true,
          last_validated: new Date().toISOString(),
          last_used: new Date().toISOString(),
        },
      };

      act(() => {
        result.current.setKeys(mockKeys);
      });

      expect(result.current.keys).toEqual(mockKeys);
    });

    it("updates existing key", () => {
      const { result } = renderHook(() => useApiKeyStore());

      const initialKey: ApiKey = {
        id: "key-1",
        service: "openai",
        has_key: true,
        is_valid: true,
        last_validated: new Date().toISOString(),
        last_used: new Date().toISOString(),
      };

      // Set initial key
      act(() => {
        result.current.setKeys({ openai: initialKey });
      });

      // Update the key
      act(() => {
        result.current.updateKey("openai", {
          has_key: true,
          is_valid: false,
        });
      });

      expect(result.current.keys.openai.has_key).toBe(true);
      expect(result.current.keys.openai.is_valid).toBe(false);
      expect(result.current.keys.openai.id).toBe("key-1"); // Should preserve original ID
    });

    it("creates new key when updating non-existent service", () => {
      const { result } = renderHook(() => useApiKeyStore());

      act(() => {
        result.current.updateKey("openai", {
          has_key: true,
          is_valid: true,
        });
      });

      expect(result.current.keys.openai).toBeDefined();
      expect(result.current.keys.openai.has_key).toBe(true);
      expect(result.current.keys.openai.is_valid).toBe(true);
    });

    it("removes key correctly", () => {
      const { result } = renderHook(() => useApiKeyStore());

      const mockKeys: Record<string, ApiKey> = {
        openai: {
          id: "key-1",
          service: "openai",
          has_key: true,
          is_valid: true,
          last_validated: new Date().toISOString(),
          last_used: new Date().toISOString(),
        },
        anthropic: {
          id: "key-2",
          service: "anthropic",
          has_key: true,
          is_valid: true,
          last_validated: new Date().toISOString(),
          last_used: new Date().toISOString(),
        },
      };

      act(() => {
        result.current.setKeys(mockKeys);
      });

      expect(Object.keys(result.current.keys)).toHaveLength(2);

      act(() => {
        result.current.removeKey("openai");
      });

      expect(Object.keys(result.current.keys)).toHaveLength(1);
      expect(result.current.keys.openai).toBeUndefined();
      expect(result.current.keys.anthropic).toBeDefined();
    });

    it("handles removing non-existent key gracefully", () => {
      const { result } = renderHook(() => useApiKeyStore());

      expect(Object.keys(result.current.keys)).toHaveLength(0);

      act(() => {
        result.current.removeKey("non-existent");
      });

      expect(Object.keys(result.current.keys)).toHaveLength(0);
    });
  });

  describe("API Key Validation", () => {
    beforeEach(() => {
      // Setup authenticated state
      act(() => {
        useApiKeyStore.setState({
          isAuthenticated: true,
          token: "mock-token",
          keys: {
            openai: {
              id: "key-1",
              service: "openai",
              has_key: true,
              is_valid: true,
              last_validated: new Date().toISOString(),
              last_used: new Date().toISOString(),
            },
          },
        });
      });
    });

    it("validates key successfully", async () => {
      const { result } = renderHook(() => useApiKeyStore());

      const mockResponse = {
        is_valid: true,
      };

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      let isValid: boolean;
      await act(async () => {
        isValid = await result.current.validateKey("openai", "sk-test123");
      });

      expect(isValid!).toBe(true);
      expect(result.current.isApiKeyValid).toBe(true);
      expect(result.current.authError).toBeNull();

      expect(global.fetch).toHaveBeenCalledWith("/api/keys/validate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer mock-token",
        },
        body: JSON.stringify({
          service: "openai",
          api_key: "sk-test123",
          save: false,
        }),
      });
    });

    it("handles validation failure", async () => {
      const { result } = renderHook(() => useApiKeyStore());

      const mockResponse = {
        is_valid: false,
        message: "Invalid API key",
      };

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      let isValid: boolean;
      await act(async () => {
        isValid = await result.current.validateKey("openai", "sk-test123");
      });

      expect(isValid!).toBe(false);
      expect(result.current.isApiKeyValid).toBe(false);
      expect(result.current.authError).toBe("Invalid API key");
    });

    it("handles API error response", async () => {
      const { result } = renderHook(() => useApiKeyStore());

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        text: async () => "API key validation failed",
      });

      let isValid: boolean;
      await act(async () => {
        isValid = await result.current.validateKey("openai", "sk-test123");
      });

      expect(isValid!).toBe(false);
      expect(result.current.isApiKeyValid).toBe(false);
      expect(result.current.authError).toBe("API key validation failed");
    });

    it("handles network error", async () => {
      const { result } = renderHook(() => useApiKeyStore());

      vi.mocked(global.fetch).mockRejectedValueOnce(new Error("Network error"));

      let isValid: boolean;
      await act(async () => {
        isValid = await result.current.validateKey("openai", "sk-test123");
      });

      expect(isValid!).toBe(false);
      expect(result.current.isApiKeyValid).toBe(false);
      expect(result.current.authError).toBe("Network error");
    });

    it("handles validation when key does not exist", async () => {
      const { result } = renderHook(() => useApiKeyStore());

      let isValid: boolean;
      await act(async () => {
        isValid = await result.current.validateKey("non-existent");
      });

      expect(isValid!).toBe(false);
      expect(result.current.authError).toBe("No API key found for non-existent");
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it("handles validation when key has no api_key field", async () => {
      const { result } = renderHook(() => useApiKeyStore());

      act(() => {
        result.current.updateKey("incomplete", { is_valid: true });
      });

      let isValid: boolean;
      await act(async () => {
        isValid = await result.current.validateKey("incomplete", "");
      });

      expect(isValid!).toBe(false);
      expect(result.current.authError).toBe("No API key found for incomplete");
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it("includes token in authorization header when available", async () => {
      const { result } = renderHook(() => useApiKeyStore());

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ is_valid: true }),
      });

      await act(async () => {
        await result.current.validateKey("openai", "sk-test123");
      });

      expect(global.fetch).toHaveBeenCalledWith("/api/keys/validate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer mock-token",
        },
        body: JSON.stringify({
          service: "openai",
          api_key: "sk-test123",
          save: false,
        }),
      });
    });

    it("omits authorization header when token not available", async () => {
      const { result } = renderHook(() => useApiKeyStore());

      // Remove token
      act(() => {
        useApiKeyStore.setState({ token: null });
      });

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ is_valid: true }),
      });

      await act(async () => {
        await result.current.validateKey("openai", "sk-test123");
      });

      expect(global.fetch).toHaveBeenCalledWith("/api/keys/validate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          service: "openai",
          api_key: "sk-test123",
          save: false,
        }),
      });
    });
  });

  describe("Load Keys", () => {
    beforeEach(() => {
      // Setup authenticated state
      act(() => {
        useApiKeyStore.setState({
          isAuthenticated: true,
          token: "mock-token",
        });
      });
    });

    it("loads keys successfully", async () => {
      const { result } = renderHook(() => useApiKeyStore());

      const mockResponse = {
        keys: {
          openai: {
            id: "key-1",
            service: "openai",
            api_key: "sk-loaded123",
            status: "active",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        },
        supported_services: ["openai", "anthropic", "google"],
      };

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await act(async () => {
        await result.current.loadKeys();
      });

      expect(result.current.keys).toEqual(mockResponse.keys);
      expect(result.current.supportedServices).toEqual(mockResponse.supported_services);

      expect(global.fetch).toHaveBeenCalledWith("/api/keys", {
        headers: {
          Authorization: "Bearer mock-token",
        },
      });
    });

    it("handles load keys API error", async () => {
      const { result } = renderHook(() => useApiKeyStore());

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
      });

      await act(async () => {
        await result.current.loadKeys();
      });

      expect(result.current.authError).toBe("Failed to load keys");
    });

    it("handles load keys network error", async () => {
      const { result } = renderHook(() => useApiKeyStore());

      vi.mocked(global.fetch).mockRejectedValueOnce(new Error("Network error"));

      await act(async () => {
        await result.current.loadKeys();
      });

      expect(result.current.authError).toBe("Network error");
    });

    it("does not load keys when not authenticated", async () => {
      const { result } = renderHook(() => useApiKeyStore());

      act(() => {
        useApiKeyStore.setState({ isAuthenticated: false });
      });

      await act(async () => {
        await result.current.loadKeys();
      });

      expect(global.fetch).not.toHaveBeenCalled();
    });

    it("does not load keys when token is missing", async () => {
      const { result } = renderHook(() => useApiKeyStore());

      act(() => {
        useApiKeyStore.setState({ token: null });
      });

      await act(async () => {
        await result.current.loadKeys();
      });

      expect(global.fetch).not.toHaveBeenCalled();
    });
  });

  describe("Error Handling", () => {
    it("handles unknown fetch error gracefully", async () => {
      const { result } = renderHook(() => useApiKeyStore());

      act(() => {
        useApiKeyStore.setState({
          isAuthenticated: true,
          token: "mock-token",
          keys: {
            openai: {
              id: "key-1",
              service: "openai",
              has_key: true,
              is_valid: true,
              last_validated: new Date().toISOString(),
              last_used: new Date().toISOString(),
            },
          },
        });
      });

      vi.mocked(global.fetch).mockRejectedValueOnce("Unknown error");

      let isValid: boolean;
      await act(async () => {
        isValid = await result.current.validateKey("openai", "sk-test123");
      });

      expect(isValid!).toBe(false);
      expect(result.current.authError).toBe("Validation failed");
    });

    it("handles non-Error exceptions in loadKeys", async () => {
      const { result } = renderHook(() => useApiKeyStore());

      act(() => {
        useApiKeyStore.setState({
          isAuthenticated: true,
          token: "mock-token",
        });
      });

      vi.mocked(global.fetch).mockRejectedValueOnce("Unknown error");

      await act(async () => {
        await result.current.loadKeys();
      });

      expect(result.current.authError).toBe("Failed to load keys");
    });
  });
});
