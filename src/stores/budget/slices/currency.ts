/**
 * @fileoverview Currency slice for the budget store.
 */

import type { CurrencyRate } from "@schemas/budget";
import type { StateCreator } from "zustand";
import type { BudgetState, BudgetStoreDeps } from "../types";

type BudgetCurrencySlice = Pick<
  BudgetState,
  | "baseCurrency"
  | "currencies"
  | "setBaseCurrency"
  | "setCurrencies"
  | "updateCurrencyRate"
>;

export const createBudgetCurrencySlice =
  (deps: BudgetStoreDeps): StateCreator<BudgetState, [], [], BudgetCurrencySlice> =>
  (set) => ({
    baseCurrency: "USD",

    currencies: {},

    setBaseCurrency: (currency) => set({ baseCurrency: currency }),

    setCurrencies: (currencies) => set({ currencies }),

    updateCurrencyRate: (code, rate) =>
      set((state) => ({
        currencies: {
          ...state.currencies,
          [code]: {
            code,
            lastUpdated: deps.nowIso(),
            rate,
          } satisfies CurrencyRate,
        },
      })),
  });
