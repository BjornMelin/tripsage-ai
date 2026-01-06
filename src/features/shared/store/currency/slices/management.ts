/**
 * @fileoverview Currency management + exchange rates slice for the currency store.
 */

"use client";

import {
  CURRENCY_SCHEMA,
  type CurrencyCode,
  EXCHANGE_RATE_SCHEMA,
  type ExchangeRate,
} from "@schemas/currency";
import type { StateCreator } from "zustand";
import { getCurrentTimestamp } from "@/features/shared/store/helpers";
import type { CurrencyStore } from "../../currency-store";
import { DEFAULT_CURRENCIES, isCurrencyCode } from "../shared";
import type { StoreLogger } from "../types";

type CurrencyManagementSlice = Pick<
  CurrencyStore,
  | "addCurrency"
  | "baseCurrency"
  | "currencies"
  | "exchangeRates"
  | "lastUpdated"
  | "removeCurrency"
  | "setBaseCurrency"
  | "updateAllExchangeRates"
  | "updateExchangeRate"
>;

export const createCurrencyManagementSlice =
  (logger: StoreLogger): StateCreator<CurrencyStore, [], [], CurrencyManagementSlice> =>
  (set) => ({
    addCurrency: (currency) => {
      const result = CURRENCY_SCHEMA.safeParse(currency);
      if (result.success) {
        set((state) => ({
          currencies: {
            ...state.currencies,
            [result.data.code]: result.data,
          },
        }));
        return true;
      }
      logger.error("Invalid currency data", { error: result.error });
      return false;
    },
    baseCurrency: "USD",
    currencies: DEFAULT_CURRENCIES,
    exchangeRates: {},
    lastUpdated: null,

    removeCurrency: (code) =>
      set((state) => {
        if (!isCurrencyCode(code)) {
          logger.error("Invalid currency code", { code });
          return state;
        }

        if (code === state.baseCurrency) return state;

        const newCurrencies = { ...state.currencies };
        const newExchangeRates = { ...state.exchangeRates };
        const newFavoriteCurrencies = state.favoriteCurrencies.filter(
          (c) => c !== code
        );

        delete newCurrencies[code];
        delete newExchangeRates[code];

        return {
          currencies: newCurrencies,
          exchangeRates: newExchangeRates,
          favoriteCurrencies: newFavoriteCurrencies,
        };
      }),

    setBaseCurrency: (currency) =>
      set((state) => {
        if (!isCurrencyCode(currency)) {
          logger.error("Invalid currency code", { currency });
          return state;
        }

        if (currency === state.baseCurrency || !state.currencies[currency]) {
          return state;
        }

        const oldBaseCurrency = state.baseCurrency;
        const baseRateEntry = state.exchangeRates[currency];
        const oldBaseRate = baseRateEntry?.rate ?? 1;
        if (!baseRateEntry) {
          logger.warn("Missing exchange rate for new base currency; assuming 1", {
            currency,
          });
        }
        if (!Number.isFinite(oldBaseRate) || oldBaseRate === 0) {
          logger.warn("Invalid exchange rate for new base currency; update dropped", {
            currency,
          });
          return state;
        }

        const timestamp = getCurrentTimestamp();
        const newExchangeRates: Record<CurrencyCode, ExchangeRate> = {};

        Object.entries(state.exchangeRates).forEach(([currencyCode, exchange]) => {
          if (!isCurrencyCode(currencyCode)) return;
          if (currencyCode === currency) return;

          let oldRate = exchange.rate;
          if (oldRate == null) {
            logger.warn("Missing exchange rate; assuming 1", { currencyCode });
            oldRate = 1;
          }
          if (!Number.isFinite(oldRate) || oldRate === 0) {
            logger.warn("Skipping currency with invalid exchange rate", {
              currencyCode,
            });
            return;
          }
          const newRate = oldRate / oldBaseRate;
          const newExchangeRate = {
            baseCurrency: currency,
            rate: newRate,
            targetCurrency: currencyCode,
            timestamp,
          };

          if (EXCHANGE_RATE_SCHEMA.safeParse(newExchangeRate).success) {
            newExchangeRates[currencyCode] = newExchangeRate;
          }
        });

        const oldBaseExchangeRate = {
          baseCurrency: currency,
          rate: 1 / oldBaseRate,
          targetCurrency: oldBaseCurrency,
          timestamp,
        };

        if (EXCHANGE_RATE_SCHEMA.safeParse(oldBaseExchangeRate).success) {
          newExchangeRates[oldBaseCurrency] = oldBaseExchangeRate;
        }

        return {
          baseCurrency: currency,
          exchangeRates: newExchangeRates,
          lastUpdated: timestamp,
        };
      }),

    updateAllExchangeRates: (rates, timestamp = getCurrentTimestamp()) =>
      set((state) => {
        const newExchangeRates: Record<CurrencyCode, ExchangeRate> = {};

        Object.entries(rates).forEach(([currencyCode, rate]) => {
          if (
            currencyCode === state.baseCurrency ||
            !isCurrencyCode(currencyCode) ||
            typeof rate !== "number" ||
            rate <= 0
          ) {
            return;
          }

          const newExchangeRate = {
            baseCurrency: state.baseCurrency,
            rate,
            targetCurrency: currencyCode,
            timestamp,
          };

          const result = EXCHANGE_RATE_SCHEMA.safeParse(newExchangeRate);
          if (result.success) {
            newExchangeRates[currencyCode] = newExchangeRate;
          }
        });

        return {
          exchangeRates: newExchangeRates,
          lastUpdated: timestamp,
        };
      }),

    updateExchangeRate: (targetCurrency, rate, timestamp = getCurrentTimestamp()) =>
      set((state) => {
        if (!isCurrencyCode(targetCurrency)) {
          logger.error("Invalid currency code", { targetCurrency });
          return state;
        }

        if (typeof rate !== "number" || rate <= 0) {
          logger.error("Invalid exchange rate", { rate });
          return state;
        }

        if (targetCurrency === state.baseCurrency) return state;

        const newExchangeRate = {
          baseCurrency: state.baseCurrency,
          rate,
          targetCurrency,
          timestamp,
        };

        const result = EXCHANGE_RATE_SCHEMA.safeParse(newExchangeRate);
        if (!result.success) {
          logger.error("Invalid exchange rate data", { error: result.error });
          return state;
        }

        return {
          exchangeRates: {
            ...state.exchangeRates,
            [targetCurrency]: newExchangeRate,
          },
          lastUpdated: timestamp,
        };
      }),
  });
