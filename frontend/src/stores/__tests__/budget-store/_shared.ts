/**
 * @fileoverview Shared test utilities and helpers for budget store tests.
 */

import { act } from "@testing-library/react";
import { useBudgetStore } from "@/stores/budget-store";

/**
 * Resets the budget store to its initial state.
 */
export const resetBudgetStore = (): void => {
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
};
