/** @vitest-environment jsdom */

import { useQuery } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/error-types";
import {
  renderWithProviders,
  resetTestQueryClient,
  screen,
  waitFor,
} from "@/test/test-utils";
import { QueryErrorBoundary } from "../query-error-boundary";

const TELEMETRY_SPY = vi.hoisted(() => vi.fn());
let retryAttempts = 0;

vi.mock("@/lib/telemetry/client-errors", () => ({
  recordClientErrorOnActiveSpan: TELEMETRY_SPY,
}));

const ThrowingComponent = ({ error }: { error: Error }) => {
  throw error;
};

const RecoveringQueryComponent = () => {
  const { data } = useQuery<string>({
    queryFn: () => {
      retryAttempts += 1;
      if (retryAttempts === 1) {
        throw new ApiError({ message: "server", status: 500 });
      }

      return "Recovered";
    },
    queryKey: ["query-error-boundary-retry"],
    retry: false,
    throwOnError: true,
  });

  return <div>{data}</div>;
};

describe("QueryErrorBoundary", () => {
  afterEach(() => {
    TELEMETRY_SPY.mockClear();
    resetTestQueryClient();
  });

  it("records telemetry with retry metadata when an error is thrown", async () => {
    renderWithProviders(
      <QueryErrorBoundary>
        <ThrowingComponent error={new ApiError({ message: "boom", status: 503 })} />
      </QueryErrorBoundary>
    );

    await screen.findByRole("button", { name: /try again/i });

    expect(TELEMETRY_SPY).toHaveBeenCalledTimes(1);
    const [errorArg, metadataArg] = TELEMETRY_SPY.mock.calls[0];

    expect(errorArg).toBeInstanceOf(Error);
    expect(metadataArg).toMatchObject({
      context: "QueryErrorBoundary",
      retryable: true,
      statusCode: 503,
      variant: "server",
    });
  });

  it("invokes injected onError asynchronously with meta", async () => {
    const handler = vi.fn();

    renderWithProviders(
      <QueryErrorBoundary onError={handler}>
        <ThrowingComponent error={new ApiError({ message: "auth", status: 401 })} />
      </QueryErrorBoundary>
    );

    await screen.findByRole("button", { name: /try again/i });

    await waitFor(() =>
      expect(handler).toHaveBeenCalledWith(
        expect.any(Error),
        expect.objectContaining({ componentStack: expect.any(String) }),
        expect.objectContaining({
          isRetryable: false,
          statusCode: 401,
          variant: "auth",
        })
      )
    );
  });

  it("invokes onOperationalAlert before onError with metadata", async () => {
    const alertHandler = vi.fn();
    const errorHandler = vi.fn();

    renderWithProviders(
      <QueryErrorBoundary onOperationalAlert={alertHandler} onError={errorHandler}>
        <ThrowingComponent error={new ApiError({ message: "server", status: 500 })} />
      </QueryErrorBoundary>
    );

    await screen.findByRole("button", { name: /try again/i });

    await waitFor(() => {
      expect(alertHandler).toHaveBeenCalledWith(
        expect.any(Error),
        expect.objectContaining({ componentStack: expect.any(String) }),
        expect.objectContaining({
          isRetryable: true,
          statusCode: 500,
          variant: "server",
        })
      );
      expect(errorHandler).toHaveBeenCalled();
      expect(alertHandler.mock.invocationCallOrder[0]).toBeLessThan(
        errorHandler.mock.invocationCallOrder[0]
      );
    });
  });

  it("disables retry UI for non-retryable errors", async () => {
    renderWithProviders(
      <QueryErrorBoundary>
        <ThrowingComponent error={new ApiError({ message: "denied", status: 403 })} />
      </QueryErrorBoundary>
    );

    const retryButton = await screen.findByRole("button", { name: /try again/i });
    expect(retryButton).toBeDisabled();
  });

  it("allows retry interaction when the error is retryable", async () => {
    const user = userEvent.setup();
    retryAttempts = 0;

    renderWithProviders(
      <QueryErrorBoundary>
        <RecoveringQueryComponent />
      </QueryErrorBoundary>
    );

    const retryButton = await screen.findByRole("button", { name: /try again/i });
    expect(retryButton).not.toBeDisabled();

    await user.click(retryButton);
    expect(await screen.findByText("Recovered")).toBeInTheDocument();
  });
});
