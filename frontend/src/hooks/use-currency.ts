/**
 * @fileoverview React hooks for currency management and conversion.
 *
 * Provides hooks for managing currencies, exchange rates, and currency conversion
 * with local state management and API synchronization.
 */

"use client";

import { useCallback, useEffect } from "react";
import { z } from "zod";
import { useApiQuery } from "@/hooks/use-api-query";
import { useCurrencyStore } from "@/stores/currency-store";
import type {
  ConversionResult,
  CurrencyCode,
  UpdateExchangeRatesResponse,
} from "@/types/currency";

/**
 * Hook for accessing currency state.
 */
export function useCurrency() {
  const { currencies, baseCurrency, exchangeRates, favoriteCurrencies, lastUpdated } =
    useCurrencyStore();

  return {
    baseCurrency,
    currencies,
    exchangeRates,
    favoriteCurrencies,
    lastUpdated,
  };
}

/**
 * Hook for currency management operations.
 */
export function useCurrencyActions() {
  const {
    setBaseCurrency,
    addCurrency,
    removeCurrency,
    addFavoriteCurrency,
    removeFavoriteCurrency,
  } = useCurrencyStore();

  return {
    addCurrency,
    addFavoriteCurrency,
    removeCurrency,
    removeFavoriteCurrency,
    setBaseCurrency,
  };
}

/**
 * Hook for exchange rate operations.
 */
export function useExchangeRates() {
  const {
    baseCurrency,
    exchangeRates,
    lastUpdated,
    updateExchangeRate,
    updateAllExchangeRates,
  } = useCurrencyStore();

  return {
    baseCurrency,
    exchangeRates,
    lastUpdated,
    updateAllExchangeRates,
    updateExchangeRate,
  };
}

/**
 * Hook for currency conversion operations.
 */
export function useCurrencyConverter() {
  const { convertAmount, formatAmountWithCurrency } = useCurrencyStore();

  const convert = useCallback(
    (amount: number, from: CurrencyCode, to: CurrencyCode): ConversionResult | null => {
      return convertAmount(amount, from, to);
    },
    [convertAmount]
  );

  const format = useCallback(
    (amount: number, currencyCode: CurrencyCode): string => {
      return formatAmountWithCurrency(amount, currencyCode);
    },
    [formatAmountWithCurrency]
  );

  const getBestRate = useCallback(
    (from: CurrencyCode, to: CurrencyCode): number | null => {
      const result = convertAmount(1, from, to);
      return result ? result.rate : null;
    },
    [convertAmount]
  );

  return {
    convert,
    format,
    getBestRate,
  };
}

/**
 * Hook for getting currency data like recent pairs and popular currencies.
 */
export function useCurrencyData() {
  const { getRecentCurrencyPairs, getPopularCurrencies, getCurrencyByCode } =
    useCurrencyStore();

  const recentPairs = getRecentCurrencyPairs();
  const popularCurrencies = getPopularCurrencies();

  return {
    getCurrencyByCode,
    popularCurrencies,
    recentPairs,
  };
}

/**
 * Hook for fetching exchange rates from API.
 */
export function useFetchExchangeRates() {
  const { updateAllExchangeRates } = useCurrencyStore();

  // Define response schema for better validation
  const responseSchema = z.object({
    baseCurrency: z.string().length(3),
    rates: z.record(z.string().length(3), z.number().positive()),
    timestamp: z.string().datetime(),
  });

  const query = useApiQuery<UpdateExchangeRatesResponse>(
    "/api/currencies/rates",
    {},
    {
      // Refresh rates every hour
      refetchInterval: 60 * 60 * 1000,
    }
  );

  useEffect(() => {
    if (query.data) {
      try {
        // Validate the response
        const validated = responseSchema.parse(query.data);
        updateAllExchangeRates(validated.rates, validated.timestamp);
      } catch (error) {
        console.error("Invalid exchange rate data:", error);
      }
    }
  }, [query.data, updateAllExchangeRates]);

  return query;
}

/**
 * Hook for fetching a specific exchange rate.
 *
 * @param targetCurrency - Currency code to fetch rate for
 */
export function useFetchExchangeRate(targetCurrency: CurrencyCode) {
  const { baseCurrency, updateExchangeRate } = useCurrencyStore();

  const query = useApiQuery<{ rate: number; timestamp: string }>(
    `/api/currencies/rates/${targetCurrency}`,
    {},
    {
      enabled: !!targetCurrency && targetCurrency !== baseCurrency,
    }
  );

  useEffect(() => {
    if (query.data) {
      updateExchangeRate(targetCurrency, query.data.rate, query.data.timestamp);
    }
  }, [query.data, targetCurrency, updateExchangeRate]);

  return query;
}
