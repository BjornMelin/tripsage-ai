/**
 * @fileoverview Currency store for managing currency data, exchange rates,
 * and currency conversion functionality using Zustand with persistence.
 */

"use client";

import type {
  ConversionResult,
  Currency,
  CurrencyCode,
  CurrencyPair,
  CurrencyState,
} from "@schemas/currency";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import { createCurrencyConversionSlice } from "./currency/slices/conversion";
import { createCurrencyFavoritesSlice } from "./currency/slices/favorites";
import { createCurrencyManagementSlice } from "./currency/slices/management";

const logger = createStoreLogger({ storeName: "currency" });

/**
 * Interface for the currency store extending base currency state with actions.
 */
export interface CurrencyStore extends CurrencyState {
  // Currency management
  /** Sets the base currency for conversions and rate calculations. */
  setBaseCurrency: (currency: CurrencyCode) => void;

  /** Adds a new currency to the store after validation. */
  addCurrency: (currency: unknown) => boolean;

  /** Removes a currency from the store and cleans up related data. */
  removeCurrency: (code: CurrencyCode) => void;

  // Exchange rate management
  /** Updates the exchange rate for a specific currency pair. */
  updateExchangeRate: (
    targetCurrency: CurrencyCode,
    rate: number,
    timestamp?: string
  ) => void;

  /** Updates multiple exchange rates at once. */
  updateAllExchangeRates: (rates: Record<string, number>, timestamp?: string) => void;

  // Favorites management
  /** Adds a currency to the favorites list. */
  addFavoriteCurrency: (code: CurrencyCode) => void;

  /** Removes a currency from the favorites list. */
  removeFavoriteCurrency: (code: CurrencyCode) => void;

  // Conversion utilities
  /** Converts an amount between two currencies. */
  convertAmount: (
    amount: number,
    fromCurrency: CurrencyCode,
    toCurrency: CurrencyCode
  ) => ConversionResult | null;

  // Additional features
  /** Gets recent currency pairs for quick access. */
  getRecentCurrencyPairs: () => CurrencyPair[];

  /** Gets the list of popular/favorite currencies. */
  getPopularCurrencies: () => Currency[];

  /** Retrieves currency information by code. */
  getCurrencyByCode: (code: string) => Currency | undefined;

  /** Formats an amount with appropriate currency symbol and locale. */
  formatAmountWithCurrency: (amount: number, currencyCode: string) => string;
}

/**
 * Zustand store hook for currency management with persistence.
 */
export const useCurrencyStore = create<CurrencyStore>()(
  devtools(
    persist(
      (...args) => ({
        ...createCurrencyManagementSlice(logger)(...args),
        ...createCurrencyFavoritesSlice(logger)(...args),
        ...createCurrencyConversionSlice(logger)(...args),
      }),
      {
        name: "currency-storage",
        partialize: (state) => ({
          // Only persist state that should be saved between sessions
          baseCurrency: state.baseCurrency,
          exchangeRates: state.exchangeRates,
          favoriteCurrencies: state.favoriteCurrencies,
          lastUpdated: state.lastUpdated,
          // Do not persist common currencies as they're defined in code
        }),
      }
    ),
    { name: "currency" }
  )
);

// Selectors
export const useBaseCurrency = () => useCurrencyStore((state) => state.baseCurrency);
export const useFavoriteCurrencies = () =>
  useCurrencyStore((state) => state.favoriteCurrencies);
export const useExchangeRates = () => useCurrencyStore((state) => state.exchangeRates);
export const useCurrencies = () => useCurrencyStore((state) => state.currencies);
export const useLastUpdated = () => useCurrencyStore((state) => state.lastUpdated);
