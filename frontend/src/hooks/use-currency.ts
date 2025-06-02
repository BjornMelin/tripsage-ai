"use client";

import { useCallback } from "react";
import { useApiQuery } from "@/hooks/use-api-query";
import { useCurrencyStore } from "@/stores/currency-store";
import type {
  CurrencyCode,
  Currency,
  ConversionResult,
  CurrencyPair,
  UpdateExchangeRatesResponse,
} from "@/types/currency";
import { z } from "zod";

/**
 * Hook for accessing currency state and basic operations
 */
export function useCurrency() {
  const {
    currencies,
    baseCurrency,
    exchangeRates,
    favoriteCurrencies,
    lastUpdated,
  } = useCurrencyStore();

  return {
    currencies,
    baseCurrency,
    exchangeRates,
    favoriteCurrencies,
    lastUpdated,
  };
}

/**
 * Hook for currency management operations
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
    setBaseCurrency,
    addCurrency,
    removeCurrency,
    addFavoriteCurrency,
    removeFavoriteCurrency,
  };
}

/**
 * Hook for exchange rate operations
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
    updateExchangeRate,
    updateAllExchangeRates,
  };
}

/**
 * Hook for currency conversion operations
 */
export function useCurrencyConverter() {
  const { convertAmount, formatAmountWithCurrency } = useCurrencyStore();

  const convert = useCallback(
    (
      amount: number,
      from: CurrencyCode,
      to: CurrencyCode
    ): ConversionResult | null => {
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
 * Hook for getting currency data like recent pairs and popular currencies
 */
export function useCurrencyData() {
  const { getRecentCurrencyPairs, getPopularCurrencies, getCurrencyByCode } =
    useCurrencyStore();

  const recentPairs = getRecentCurrencyPairs();
  const popularCurrencies = getPopularCurrencies();

  return {
    recentPairs,
    popularCurrencies,
    getCurrencyByCode,
  };
}

/**
 * Hook for fetching exchange rates from API
 */
export function useFetchExchangeRates() {
  const { updateAllExchangeRates } = useCurrencyStore();

  // Define response schema for better validation
  const responseSchema = z.object({
    baseCurrency: z.string().length(3),
    rates: z.record(z.string().length(3), z.number().positive()),
    timestamp: z.string().datetime(),
  });

  return useApiQuery<UpdateExchangeRatesResponse>(
    "/api/currencies/rates",
    {},
    {
      onSuccess: (data) => {
        try {
          // Validate the response
          const validated = responseSchema.parse(data);
          updateAllExchangeRates(validated.rates, validated.timestamp);
        } catch (error) {
          console.error("Invalid exchange rate data:", error);
        }
      },
      // Refresh rates every hour
      refetchInterval: 60 * 60 * 1000,
    }
  );
}

/**
 * Hook for fetching a specific exchange rate
 */
export function useFetchExchangeRate(targetCurrency: CurrencyCode) {
  const { baseCurrency, updateExchangeRate } = useCurrencyStore();

  return useApiQuery<{ rate: number; timestamp: string }>(
    `/api/currencies/rates/${targetCurrency}`,
    {},
    {
      onSuccess: (data) => {
        updateExchangeRate(targetCurrency, data.rate, data.timestamp);
      },
      enabled: !!targetCurrency && targetCurrency !== baseCurrency,
    }
  );
}
