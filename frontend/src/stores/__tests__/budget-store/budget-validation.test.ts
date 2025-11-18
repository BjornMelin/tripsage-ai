/** @vitest-environment jsdom */

import { act } from "@testing-library/react";
import { beforeEach, describe } from "vitest";
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

  // Validation tests will be added here when validation logic is implemented
});
