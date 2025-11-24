/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";
import { apiClient } from "@/lib/api/api-client";
import { ApiError } from "@/lib/api/error-types";

vi.mock("@/lib/api/api-client", () => ({
  apiClient: {
    delete: vi.fn(),
    get: vi.fn(),
    patch: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

const MOCKED_API_GET = vi.mocked(apiClient.get);

describe("useAuthenticatedApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MOCKED_API_GET.mockResolvedValue({ ok: true } as unknown as Response);
  });

  it("normalizes /api/ prefix and forwards calls to apiClient", async () => {
    const { result } = renderHook(() => useAuthenticatedApi());

    await act(async () => {
      await result.current.authenticatedApi.get("/api/ping");
    });

    expect(MOCKED_API_GET).toHaveBeenCalledTimes(1);
    const [endpoint] = MOCKED_API_GET.mock.calls[0] ?? [];
    expect(endpoint).toBe("ping");
  });

  it("propagates ApiError instances from the underlying client", async () => {
    MOCKED_API_GET.mockRejectedValueOnce(
      new ApiError({ code: "RATE_LIMITED", message: "429", status: 429 })
    );

    const { result } = renderHook(() => useAuthenticatedApi());

    await expect(
      act(async () => {
        await result.current.authenticatedApi.get("/api/ping");
      })
    ).rejects.toThrow(ApiError);

    expect(MOCKED_API_GET).toHaveBeenCalledTimes(1);
  });

  it("wraps non-ApiError failures into ApiError with NETWORK_ERROR code", async () => {
    MOCKED_API_GET.mockRejectedValueOnce(new Error("boom"));

    const { result } = renderHook(() => useAuthenticatedApi());

    await expect(
      act(async () => {
        await result.current.authenticatedApi.get("/api/ping");
      })
    ).rejects.toMatchObject(
      new ApiError({ code: "NETWORK_ERROR", message: "boom", status: 0 })
    );

    expect(MOCKED_API_GET).toHaveBeenCalledTimes(1);
  });
});
