import { describe, expect, it } from "vitest";

import type { AgentWorkflow } from "@/schemas/agents";

import { buildRateLimit } from "../config";

describe("buildRateLimit", () => {
  const testIdentifier = "test-identifier-123";

  it("returns expected structure for flightSearch workflow", () => {
    const result = buildRateLimit("flightSearch", testIdentifier);
    expect(result).toEqual({
      identifier: testIdentifier,
      limit: 8,
      window: "1 m",
    });
  });

  it("returns expected structure for accommodationSearch workflow", () => {
    const result = buildRateLimit("accommodationSearch", testIdentifier);
    expect(result).toEqual({
      identifier: testIdentifier,
      limit: 10,
      window: "1 m",
    });
  });

  it("returns expected structure for budgetPlanning workflow", () => {
    const result = buildRateLimit("budgetPlanning", testIdentifier);
    expect(result).toEqual({
      identifier: testIdentifier,
      limit: 6,
      window: "1 m",
    });
  });

  it("returns expected structure for memoryUpdate workflow", () => {
    const result = buildRateLimit("memoryUpdate", testIdentifier);
    expect(result).toEqual({
      identifier: testIdentifier,
      limit: 20,
      window: "1 m",
    });
  });

  it("returns expected structure for destinationResearch workflow", () => {
    const result = buildRateLimit("destinationResearch", testIdentifier);
    expect(result).toEqual({
      identifier: testIdentifier,
      limit: 8,
      window: "1 m",
    });
  });

  it("returns expected structure for itineraryPlanning workflow", () => {
    const result = buildRateLimit("itineraryPlanning", testIdentifier);
    expect(result).toEqual({
      identifier: testIdentifier,
      limit: 6,
      window: "1 m",
    });
  });

  it("returns expected structure for router workflow", () => {
    const result = buildRateLimit("router", testIdentifier);
    expect(result).toEqual({
      identifier: testIdentifier,
      limit: 100,
      window: "1 m",
    });
  });

  it("uses consistent window across all workflows", () => {
    const workflows: AgentWorkflow[] = [
      "flightSearch",
      "accommodationSearch",
      "budgetPlanning",
      "memoryUpdate",
      "destinationResearch",
      "itineraryPlanning",
      "router",
    ];

    const results = workflows.map((workflow) =>
      buildRateLimit(workflow, testIdentifier)
    );

    const windows = results.map((r) => r.window);
    const uniqueWindows = new Set(windows);
    expect(uniqueWindows.size).toBe(1);
    expect(windows[0]).toBe("1 m");
  });

  it("preserves identifier across different workflows", () => {
    const workflows: AgentWorkflow[] = [
      "flightSearch",
      "accommodationSearch",
      "budgetPlanning",
    ];

    const results = workflows.map((workflow) =>
      buildRateLimit(workflow, testIdentifier)
    );

    results.forEach((result) => {
      expect(result.identifier).toBe(testIdentifier);
    });
  });

  it("returns different limits for different workflows", () => {
    const flightLimit = buildRateLimit("flightSearch", testIdentifier).limit;
    const accommodationLimit = buildRateLimit(
      "accommodationSearch",
      testIdentifier
    ).limit;
    const memoryLimit = buildRateLimit("memoryUpdate", testIdentifier).limit;

    expect(flightLimit).toBe(8);
    expect(accommodationLimit).toBe(10);
    expect(memoryLimit).toBe(20);
    expect(flightLimit).not.toBe(accommodationLimit);
    expect(accommodationLimit).not.toBe(memoryLimit);
  });
});
