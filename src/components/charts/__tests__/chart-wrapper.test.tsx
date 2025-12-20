/** @vitest-environment jsdom */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WithRecharts } from "../chart-wrapper";

type RechartsModule = typeof import("recharts");

function CreateDeferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;

  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });

  return { promise, reject, resolve };
}

describe("WithRecharts", () => {
  it("renders fallback while loading then renders children on success", async () => {
    const loadRecharts = vi
      .fn<() => Promise<RechartsModule>>()
      .mockResolvedValue({} as RechartsModule);

    render(
      <WithRecharts
        fallback={<div data-testid="fallback">Loading…</div>}
        loadRecharts={loadRecharts}
      >
        {() => <div data-testid="loaded">Loaded</div>}
      </WithRecharts>
    );

    expect(screen.getByTestId("fallback")).toBeInTheDocument();
    expect(loadRecharts).toHaveBeenCalledTimes(1);

    expect(await screen.findByTestId("loaded")).toBeInTheDocument();
  });

  it("shows error UI and retries loading, preserving fallback layout", async () => {
    const frameStyle = { height: 123, width: "100%" } as const;
    const loadRecharts = vi
      .fn<() => Promise<RechartsModule>>()
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce({} as RechartsModule);

    render(
      <WithRecharts
        fallback={
          <div data-testid="frame" style={frameStyle}>
            Loading…
          </div>
        }
        loadRecharts={loadRecharts}
      >
        {() => <div data-testid="loaded">Loaded</div>}
      </WithRecharts>
    );

    expect(loadRecharts).toHaveBeenCalledTimes(1);

    const frame = await screen.findByTestId("frame");
    expect(frame).toHaveStyle({ height: "123px", width: "100%" });
    expect(screen.getByText("Failed to load chart.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => {
      expect(loadRecharts).toHaveBeenCalledTimes(2);
    });

    expect(await screen.findByTestId("loaded")).toBeInTheDocument();
  });

  it("avoids state updates after unmount during async load", async () => {
    const deferred = CreateDeferred<RechartsModule>();
    const loadRecharts = vi
      .fn<() => Promise<RechartsModule>>()
      .mockReturnValue(deferred.promise);
    const consoleErrorSpy = vi
      .spyOn(console, "error")
      .mockImplementation(() => undefined);

    const { unmount } = render(
      <WithRecharts loadRecharts={loadRecharts}>
        {() => <div data-testid="loaded">Loaded</div>}
      </WithRecharts>
    );

    unmount();
    deferred.resolve({} as RechartsModule);

    await Promise.resolve();

    expect(consoleErrorSpy).not.toHaveBeenCalled();
    consoleErrorSpy.mockRestore();
  });
});
