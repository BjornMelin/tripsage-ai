/** @vitest-environment jsdom */

import { act, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiKeysContent } from "@/components/settings/api-keys-content";
import { render } from "@/test/test-utils";

const { mockAuthenticatedApi, mockCancelRequests } = vi.hoisted(() => ({
  mockAuthenticatedApi: {
    delete: vi.fn(),
    get: vi.fn(),
    post: vi.fn(),
  },
  mockCancelRequests: vi.fn(),
}));

vi.mock("@/hooks/use-authenticated-api", () => ({
  useAuthenticatedApi: () => ({
    authenticatedApi: mockAuthenticatedApi,
    cancelRequests: mockCancelRequests,
  }),
}));

vi.mock("@/app/(app)/dashboard/settings/api-keys/actions", () => ({
  updateGatewayFallbackPreference: vi.fn().mockResolvedValue({ ok: true }),
}));

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
};

describe("ApiKeysContent", () => {
  const createDeferred = <T,>(): Deferred<T> => {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((promiseResolve) => {
      resolve = promiseResolve;
    });
    return { promise, resolve };
  };

  beforeEach(() => {
    mockAuthenticatedApi.delete.mockReset();
    mockAuthenticatedApi.get.mockReset();
    mockAuthenticatedApi.post.mockReset();
    mockCancelRequests.mockReset();
  });

  it("starts key summary and user setting reads concurrently on initial load", async () => {
    const keysRequest =
      createDeferred<
        Array<{
          createdAt: string;
          hasKey: boolean;
          isValid: boolean;
          service: "openai";
        }>
      >();
    const settingsRequest = createDeferred<{
      allowGatewayFallback: boolean | null;
    }>();

    mockAuthenticatedApi.get.mockImplementation((endpoint: string) => {
      if (endpoint === "/api/keys") return keysRequest.promise;
      if (endpoint === "/api/user-settings") return settingsRequest.promise;
      throw new Error(`Unexpected endpoint: ${endpoint}`);
    });

    render(<ApiKeysContent />);

    await waitFor(() => {
      expect(mockAuthenticatedApi.get).toHaveBeenCalledWith("/api/keys");
      expect(mockAuthenticatedApi.get).toHaveBeenCalledWith("/api/user-settings");
    });

    await act(async () => {
      keysRequest.resolve([
        {
          createdAt: "2026-01-01T00:00:00.000Z",
          hasKey: true,
          isValid: true,
          service: "openai",
        },
      ]);
      settingsRequest.resolve({ allowGatewayFallback: true });
      await Promise.all([keysRequest.promise, settingsRequest.promise]);
    });

    expect(
      await screen.findByRole("combobox", { name: "Provider" })
    ).toBeInTheDocument();
    expect(screen.getByLabelText("API Key")).toBeInTheDocument();
    await expect(
      screen.getByRole("switch", { name: "Allow fallback to team Gateway" })
    ).toHaveAccessibleDescription(
      "When no BYOK key is present, permit using the team Vercel AI Gateway. You can change this at any time. Some features may require an active provider key if disabled."
    );
  });
});
