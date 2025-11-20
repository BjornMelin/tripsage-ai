/** @vitest-environment jsdom */

import { act } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useBudgetStore } from "@/stores/budget-store";

describe("Budget Store - Budget Validation", () => {
  beforeEach(() => {
    act(() => {
      useBudgetStore.setState({
        activeBudgetId: null,
        alerts: {},
        baseCurrency: "USD",
        budgets: {},
        currencies: {},
        expenses: {},
      });
    });
  });

  it("resets budgets state before validation flows", () => {
    const state = useBudgetStore.getState();
    expect(state.budgets).toEqual({});
    expect(state.activeBudgetId).toBeNull();
  });
});
