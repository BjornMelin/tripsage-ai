/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

const RECORD_CLIENT_ERROR_SPY = vi.hoisted(() => vi.fn());

vi.mock("@/lib/telemetry/client-errors", () => ({
  recordClientErrorOnActiveSpan: RECORD_CLIENT_ERROR_SPY,
}));

import { createStoreLogger } from "../store-logger";

interface ErrorWithDetails extends Error {
  details?: Record<string, unknown>;
}

describe("createStoreLogger", () => {
  beforeEach(() => {
    RECORD_CLIENT_ERROR_SPY.mockReset();
  });

  it("records errors on the active client span with store metadata", () => {
    const logger = createStoreLogger({
      metadata: { slice: "filters" },
      storeName: "search-store",
    });

    logger.error("Invalid filter state", { filterId: "price" });

    expect(RECORD_CLIENT_ERROR_SPY).toHaveBeenCalledTimes(1);
    const [captured] = RECORD_CLIENT_ERROR_SPY.mock.calls[0] ?? [];
    const error = captured as ErrorWithDetails;
    expect(error).toBeInstanceOf(Error);
    expect(error.message).toBe("[search-store] Invalid filter state");
    expect(error.details).toEqual({
      filterId: "price",
      slice: "filters",
      storeName: "search-store",
    });
  });

  it("does not emit raw console diagnostics for non-error events", () => {
    const logSpy = vi.spyOn(console, "log").mockImplementation(() => undefined);
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const logger = createStoreLogger({ storeName: "ui-store" });

    logger.info("Theme changed", { theme: "dark" });
    logger.warn("Theme listener unavailable", { reason: "matchMedia" });

    expect(logSpy).not.toHaveBeenCalled();
    expect(warnSpy).not.toHaveBeenCalled();
    expect(RECORD_CLIENT_ERROR_SPY).not.toHaveBeenCalled();

    logSpy.mockRestore();
    warnSpy.mockRestore();
  });
});
