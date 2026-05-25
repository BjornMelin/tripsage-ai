/** @vitest-environment jsdom */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@/test/test-utils";
import { FilterRange } from "../filter-range";

const { mockRecordClientErrorOnActiveSpan } = vi.hoisted(() => ({
  mockRecordClientErrorOnActiveSpan: vi.fn(),
}));

vi.mock("@/lib/telemetry/client-errors", () => ({
  recordClientErrorOnActiveSpan: mockRecordClientErrorOnActiveSpan,
}));

describe("FilterRange", () => {
  beforeEach(() => {
    mockRecordClientErrorOnActiveSpan.mockReset();
  });

  it("renders the configured range label and current value", () => {
    render(
      <FilterRange
        filterId="price_range"
        label="Price"
        min={0}
        max={2000}
        value={{ max: 500, min: 100 }}
        onChange={vi.fn()}
        formatValue={(value) => `$${value}`}
      />
    );

    expect(screen.getByText("Price")).toBeInTheDocument();
    expect(screen.getByText("$100 – $500")).toBeInTheDocument();
    expect(mockRecordClientErrorOnActiveSpan).not.toHaveBeenCalled();
  });

  it("reports invalid configuration through telemetry and renders nothing", () => {
    render(
      <FilterRange
        filterId="price_range"
        label="Price"
        min={100}
        max={100}
        step={0}
        onChange={vi.fn()}
      />
    );

    expect(screen.queryByText("Price")).not.toBeInTheDocument();
    expect(mockRecordClientErrorOnActiveSpan).toHaveBeenCalledWith(expect.any(Error), {
      action: "validateConfig",
      context: "FilterRange",
      filterId: "price_range",
      max: 100,
      min: 100,
      step: 0,
    });
  });

  it("keeps the null-render fallback when telemetry recording fails", () => {
    mockRecordClientErrorOnActiveSpan.mockImplementationOnce(() => {
      throw new Error("telemetry unavailable");
    });

    render(
      <FilterRange
        filterId="duration"
        label="Duration"
        min={60}
        max={30}
        onChange={vi.fn()}
      />
    );

    expect(screen.queryByText("Duration")).not.toBeInTheDocument();
    expect(mockRecordClientErrorOnActiveSpan).toHaveBeenCalledWith(expect.any(Error), {
      action: "validateConfig",
      context: "FilterRange",
      filterId: "duration",
      max: 30,
      min: 60,
      step: 1,
    });
  });
});
