/**
 * @fileoverview Conversion + formatting slice for the currency store.
 */

"use client";

import {
  CONVERSION_RESULT_SCHEMA,
  CURRENCY_CODE_SCHEMA,
  type Currency,
  type CurrencyPair,
} from "@schemas/currency";
import type { StateCreator } from "zustand";
import { getCurrentTimestamp } from "@/features/shared/store/helpers";
import type { CurrencyStore } from "../../currency-store";
import { isCurrencyCode } from "../shared";
import type { StoreLogger } from "../types";

type CurrencyConversionSlice = Pick<
  CurrencyStore,
  | "convertAmount"
  | "formatAmountWithCurrency"
  | "getCurrencyByCode"
  | "getPopularCurrencies"
  | "getRecentCurrencyPairs"
>;

export const createCurrencyConversionSlice =
  (logger: StoreLogger): StateCreator<CurrencyStore, [], [], CurrencyConversionSlice> =>
  (_set, get) => {
    const safeParseConversionResult = (value: unknown) => {
      const parsed = CONVERSION_RESULT_SCHEMA.safeParse(value);
      if (!parsed.success) {
        logger.error("Invalid conversion result", { error: parsed.error });
        return null;
      }
      return parsed.data;
    };

    return {
      convertAmount: (amount, fromCurrency, toCurrency) => {
        const state = get();

        if (
          typeof amount !== "number" ||
          !Number.isFinite(amount) ||
          !isCurrencyCode(fromCurrency) ||
          !isCurrencyCode(toCurrency)
        ) {
          logger.error("Invalid conversion parameters", {
            amount,
            fromCurrency,
            toCurrency,
          });
          return null;
        }

        if (fromCurrency === toCurrency) {
          const result = {
            fromAmount: amount,
            fromCurrency,
            rate: 1,
            timestamp: getCurrentTimestamp(),
            toAmount: amount,
            toCurrency,
          };

          return safeParseConversionResult(result);
        }

        if (fromCurrency === state.baseCurrency) {
          const exchangeRate = state.exchangeRates[toCurrency];
          if (!exchangeRate) {
            logger.warn("Missing exchange rate for target currency", {
              amount,
              baseCurrency: state.baseCurrency,
              fromCurrency,
              toCurrency,
            });
            return null;
          }
          if (
            typeof exchangeRate.rate !== "number" ||
            !Number.isFinite(exchangeRate.rate) ||
            exchangeRate.rate <= 0
          ) {
            logger.error("Invalid target currency exchange rate", {
              exchangeRate,
              toCurrency,
            });
            return null;
          }

          const convertedAmount = amount * exchangeRate.rate;
          const result = {
            fromAmount: amount,
            fromCurrency,
            rate: exchangeRate.rate,
            timestamp: exchangeRate.timestamp,
            toAmount: convertedAmount,
            toCurrency,
          };
          return safeParseConversionResult(result);
        }

        if (toCurrency === state.baseCurrency) {
          const exchangeRate = state.exchangeRates[fromCurrency];
          if (!exchangeRate) {
            logger.warn("Missing exchange rate for source currency", {
              amount,
              baseCurrency: state.baseCurrency,
              fromCurrency,
              toCurrency,
            });
            return null;
          }
          if (
            typeof exchangeRate.rate !== "number" ||
            !Number.isFinite(exchangeRate.rate) ||
            exchangeRate.rate <= 0
          ) {
            logger.error("Invalid source currency exchange rate", {
              exchangeRate,
              fromCurrency,
            });
            return null;
          }

          const convertedAmount = amount / exchangeRate.rate;
          const result = {
            fromAmount: amount,
            fromCurrency,
            rate: 1 / exchangeRate.rate,
            timestamp: exchangeRate.timestamp,
            toAmount: convertedAmount,
            toCurrency,
          };
          return safeParseConversionResult(result);
        }

        const fromExchangeRate = state.exchangeRates[fromCurrency];
        const toExchangeRate = state.exchangeRates[toCurrency];

        if (!fromExchangeRate || !toExchangeRate) {
          logger.warn("Missing exchange rate for cross-currency conversion", {
            amount,
            baseCurrency: state.baseCurrency,
            fromCurrency,
            hasFromRate: Boolean(fromExchangeRate),
            hasToRate: Boolean(toExchangeRate),
            toCurrency,
          });
          return null;
        }
        if (
          typeof fromExchangeRate.rate !== "number" ||
          !Number.isFinite(fromExchangeRate.rate) ||
          fromExchangeRate.rate <= 0 ||
          typeof toExchangeRate.rate !== "number" ||
          !Number.isFinite(toExchangeRate.rate) ||
          toExchangeRate.rate <= 0
        ) {
          logger.error("Invalid exchange rates for conversion", {
            fromCurrency,
            fromExchangeRate,
            toCurrency,
            toExchangeRate,
          });
          return null;
        }

        const amountInBaseCurrency = amount / fromExchangeRate.rate;
        const convertedAmount = amountInBaseCurrency * toExchangeRate.rate;
        const effectiveRate = toExchangeRate.rate / fromExchangeRate.rate;
        const result = {
          fromAmount: amount,
          fromCurrency,
          rate: effectiveRate,
          timestamp: getCurrentTimestamp(),
          toAmount: convertedAmount,
          toCurrency,
        };

        return safeParseConversionResult(result);
      },

      formatAmountWithCurrency: (amount, currencyCode) => {
        const state = get();
        const result = CURRENCY_CODE_SCHEMA.safeParse(currencyCode);

        if (!result.success) {
          return `${amount} ${currencyCode}`;
        }

        const code = result.data;
        const currency = state.currencies[code];

        if (!currency) {
          return `${amount} ${code}`;
        }

        try {
          return new Intl.NumberFormat(undefined, {
            currency: code,
            maximumFractionDigits: currency.decimals,
            minimumFractionDigits: currency.decimals,
            style: "currency",
          }).format(amount);
        } catch (error) {
          logger.error("Error formatting currency", { code, error });
          return `${amount} ${code}`;
        }
      },

      getCurrencyByCode: (code) => {
        const state = get();
        const result = CURRENCY_CODE_SCHEMA.safeParse(code);
        if (result.success) {
          return state.currencies[result.data];
        }
        return undefined;
      },

      getPopularCurrencies: (): Currency[] => {
        const state = get();
        return state.favoriteCurrencies
          .map((code) => state.currencies[code])
          .filter((currency): currency is Currency => currency !== undefined);
      },

      getRecentCurrencyPairs: (): CurrencyPair[] => {
        const state = get();
        return state.favoriteCurrencies
          .filter((code) => code !== state.baseCurrency)
          .map((code) => ({ fromCurrency: state.baseCurrency, toCurrency: code }));
      },
    };
  };
