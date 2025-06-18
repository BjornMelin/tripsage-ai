import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useAddApiKey, useApiKeys, useDeleteApiKey, useValidateApiKey } from "../use-api-keys";

// Mock the dependencies
const mockSetKeys = vi.fn();
const mockSetSupportedServices = vi.fn();
const mockUpdateKey = vi.fn();
const mockRemoveKey = vi.fn();
const mockInvalidateQueries = vi.fn();

vi.mock("@/stores/api-key-store", () => ({
  useApiKeyStore: vi.fn(() => ({
    setKeys: mockSetKeys,
    setSupportedServices: mockSetSupportedServices,
    updateKey: mockUpdateKey,
    removeKey: mockRemoveKey,
  })),
}));

vi.mock("@tanstack/react-query", () => ({
  useQueryClient: vi.fn(() => ({
    invalidateQueries: mockInvalidateQueries,
  })),
}));

// Mock the API hooks
vi.mock("@/hooks/use-api-query", () => ({
  useApiQuery: vi.fn(),
  useApiMutation: vi.fn(),
  useApiDeleteMutation: vi.fn(),
}));

describe("useApiKeys", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should call useApiQuery with correct endpoint", () => {
    const mockQueryResult = {
      data: null,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    };
    
    const { useApiQuery } = await import("@/hooks/use-api-query");
    vi.mocked(useApiQuery).mockReturnValue(mockQueryResult);

    renderHook(() => useApiKeys());

    expect(mockUseApiQuery).toHaveBeenCalledWith("/api/user/keys", {});
  });

  it("should update store when data is received", async () => {
    const mockData = {
      keys: {
        "google-maps": { is_valid: true, has_key: true, service: "google-maps" },
        "openai": { is_valid: false, has_key: true, service: "openai" },
      },
      supported_services: ["google-maps", "openai", "weather"],
    };

    const mockQueryResult = {
      data: mockData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };

    const { useApiQuery } = await import("@/hooks/use-api-query");
    vi.mocked(useApiQuery).mockReturnValue(mockQueryResult);

    renderHook(() => useApiKeys());

    await waitFor(() => {
      expect(mockSetKeys).toHaveBeenCalledWith(mockData.keys);
      expect(mockSetSupportedServices).toHaveBeenCalledWith(mockData.supported_services);
    });
  });

  it("should not update store when no data", () => {
    const mockQueryResult = {
      data: null,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    };

    const { useApiQuery } = await import("@/hooks/use-api-query");
    vi.mocked(useApiQuery).mockReturnValue(mockQueryResult);

    renderHook(() => useApiKeys());

    expect(mockSetKeys).not.toHaveBeenCalled();
    expect(mockSetSupportedServices).not.toHaveBeenCalled();
  });

  it("should return query result", () => {
    const mockQueryResult = {
      data: null,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    };

    mockUseApiQuery.mockReturnValue(mockQueryResult);

    const { result } = renderHook(() => useApiKeys());

    expect(result.current).toBe(mockQueryResult);
  });
});

describe("useAddApiKey", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should call useApiMutation with correct endpoint", () => {
    const mockMutationResult = {
      data: null,
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
      isSuccess: false,
      error: null,
    };

    mockUseApiMutation.mockReturnValue(mockMutationResult);

    renderHook(() => useAddApiKey());

    expect(mockUseApiMutation).toHaveBeenCalledWith("/api/user/keys");
  });

  it("should update store and invalidate queries when data is received", async () => {
    const mockData = {
      service: "google-maps",
      is_valid: true,
    };

    const mockMutationResult = {
      data: mockData,
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
      isSuccess: true,
      error: null,
    };

    mockUseApiMutation.mockReturnValue(mockMutationResult);

    renderHook(() => useAddApiKey());

    await waitFor(() => {
      expect(mockUpdateKey).toHaveBeenCalledWith("google-maps", {
        is_valid: true,
        has_key: true,
        service: "google-maps",
        last_validated: expect.any(String),
      });
      expect(mockInvalidateQueries).toHaveBeenCalledWith({
        queryKey: ["/api/user/keys"],
      });
    });
  });

  it("should not update store when no data", () => {
    const mockMutationResult = {
      data: null,
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: true,
      isError: false,
      isSuccess: false,
      error: null,
    };

    mockUseApiMutation.mockReturnValue(mockMutationResult);

    renderHook(() => useAddApiKey());

    expect(mockUpdateKey).not.toHaveBeenCalled();
    expect(mockInvalidateQueries).not.toHaveBeenCalled();
  });

  it("should return mutation result", () => {
    const mockMutationResult = {
      data: null,
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
      isSuccess: false,
      error: null,
    };

    mockUseApiMutation.mockReturnValue(mockMutationResult);

    const { result } = renderHook(() => useAddApiKey());

    expect(result.current).toBe(mockMutationResult);
  });
});

describe("useValidateApiKey", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should call useApiMutation with validate endpoint", () => {
    const mockMutationResult = {
      data: null,
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
      isSuccess: false,
      error: null,
    };

    mockUseApiMutation.mockReturnValue(mockMutationResult);

    renderHook(() => useValidateApiKey());

    expect(mockUseApiMutation).toHaveBeenCalledWith("/api/user/keys/validate");
  });

  it("should return mutation result", () => {
    const mockMutationResult = {
      data: null,
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
      isSuccess: false,
      error: null,
    };

    mockUseApiMutation.mockReturnValue(mockMutationResult);

    const { result } = renderHook(() => useValidateApiKey());

    expect(result.current).toBe(mockMutationResult);
  });

  it("should not affect store state", () => {
    const mockMutationResult = {
      data: { service: "openai", is_valid: true },
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
      isSuccess: true,
      error: null,
    };

    mockUseApiMutation.mockReturnValue(mockMutationResult);

    renderHook(() => useValidateApiKey());

    expect(mockUpdateKey).not.toHaveBeenCalled();
    expect(mockInvalidateQueries).not.toHaveBeenCalled();
  });
});

describe("useDeleteApiKey", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should call useApiDeleteMutation with correct endpoint", () => {
    const mockMutationResult = {
      data: null,
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
      isSuccess: false,
      error: null,
    };

    mockUseApiDeleteMutation.mockReturnValue(mockMutationResult);

    renderHook(() => useDeleteApiKey());

    expect(mockUseApiDeleteMutation).toHaveBeenCalledWith("/api/user/keys");
  });

  it("should update store and invalidate queries when successful", async () => {
    const mockData = {
      success: true,
      service: "google-maps",
    };

    const mockMutationResult = {
      data: mockData,
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
      isSuccess: true,
      error: null,
    };

    mockUseApiDeleteMutation.mockReturnValue(mockMutationResult);

    renderHook(() => useDeleteApiKey());

    await waitFor(() => {
      expect(mockRemoveKey).toHaveBeenCalledWith("google-maps");
      expect(mockInvalidateQueries).toHaveBeenCalledWith({
        queryKey: ["/api/user/keys"],
      });
    });
  });

  it("should not update store when deletion fails", () => {
    const mockData = {
      success: false,
      service: "google-maps",
    };

    const mockMutationResult = {
      data: mockData,
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
      isSuccess: true,
      error: null,
    };

    mockUseApiDeleteMutation.mockReturnValue(mockMutationResult);

    renderHook(() => useDeleteApiKey());

    expect(mockRemoveKey).not.toHaveBeenCalled();
    expect(mockInvalidateQueries).not.toHaveBeenCalled();
  });

  it("should not update store when no data", () => {
    const mockMutationResult = {
      data: null,
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: true,
      isError: false,
      isSuccess: false,
      error: null,
    };

    mockUseApiDeleteMutation.mockReturnValue(mockMutationResult);

    renderHook(() => useDeleteApiKey());

    expect(mockRemoveKey).not.toHaveBeenCalled();
    expect(mockInvalidateQueries).not.toHaveBeenCalled();
  });

  it("should return mutation result", () => {
    const mockMutationResult = {
      data: null,
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
      isSuccess: false,
      error: null,
    };

    mockUseApiDeleteMutation.mockReturnValue(mockMutationResult);

    const { result } = renderHook(() => useDeleteApiKey());

    expect(result.current).toBe(mockMutationResult);
  });
});

describe("Integration Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should handle multiple API operations in sequence", async () => {
    // Test fetch, add, validate, delete sequence
    const fetchResult = {
      data: {
        keys: {},
        supported_services: ["google-maps"],
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };

    const addResult = {
      data: {
        service: "google-maps",
        is_valid: true,
      },
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
      isSuccess: true,
      error: null,
    };

    const validateResult = {
      data: {
        service: "google-maps",
        is_valid: true,
      },
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
      isSuccess: true,
      error: null,
    };

    const deleteResult = {
      data: {
        success: true,
        service: "google-maps",
      },
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
      isSuccess: true,
      error: null,
    };

    mockUseApiQuery.mockReturnValue(fetchResult);
    mockUseApiMutation.mockReturnValue(addResult);
    mockUseApiDeleteMutation.mockReturnValue(deleteResult);

    // Render all hooks
    const { result: fetchHook } = renderHook(() => useApiKeys());
    const { result: addHook } = renderHook(() => useAddApiKey());
    const { result: validateHook } = renderHook(() => useValidateApiKey());
    const { result: deleteHook } = renderHook(() => useDeleteApiKey());

    await waitFor(() => {
      // Verify fetch hook updated store
      expect(mockSetKeys).toHaveBeenCalledWith({});
      expect(mockSetSupportedServices).toHaveBeenCalledWith(["google-maps"]);

      // Verify add hook updated store
      expect(mockUpdateKey).toHaveBeenCalledWith("google-maps", {
        is_valid: true,
        has_key: true,
        service: "google-maps",
        last_validated: expect.any(String),
      });

      // Verify delete hook updated store
      expect(mockRemoveKey).toHaveBeenCalledWith("google-maps");

      // Verify invalidation was called for both add and delete
      expect(mockInvalidateQueries).toHaveBeenCalledTimes(2);
    });

    // Verify all hooks return their respective results
    expect(fetchHook.current).toBe(fetchResult);
    expect(addHook.current).toBe(addResult);
    expect(validateHook.current).toBe(validateResult);
    expect(deleteHook.current).toBe(deleteResult);
  });
});