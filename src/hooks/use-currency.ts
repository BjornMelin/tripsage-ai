/**
 * @fileoverview React hooks for currency management and conversion.
 */

"use client";

import type {
  ConversionResult,
  CurrencyCode,
  UpdateExchangeRatesResponse,
} from "@schemas/currency";
import { UPDATE_EXCHANGE_RATES_RESPONSE_SCHEMA } from "@schemas/currency";
import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect } from "react";
import { useCurrencyStore } from "@/features/shared/store/currency-store";
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";
import { type AppError, handleApiError, isApiError } from "@/lib/api/error-types";
import { staleTimes } from "@/lib/query/config";
import { queryKeys } from "@/lib/query-keys";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";

const MAX_CURRENCY_QUERY_RETRIES = 2;

/**
 * React Query retry policy for currency fetches.
 *
 * @param failureCount - The number of consecutive failures so far.
 * @param error - Normalized application error for the failed request.
 * @returns True when the query should be retried, otherwise false.
 */
function shouldRetryCurrencyQuery(failureCount: number, error: AppError): boolean {
  if (isApiError(error) && (error.status === 401 || error.status === 403)) {
    return false;
  }
  return failureCount < MAX_CURRENCY_QUERY_RETRIES && error.shouldRetry;
}

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
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  const query = useQuery<UpdateExchangeRatesResponse, AppError>({
    queryFn: async () => {
      try {
        return await makeAuthenticatedRequest<UpdateExchangeRatesResponse>(
          "/api/currencies/rates"
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey: queryKeys.currency.rates(),
    refetchInterval: 60 * 60 * 1000, // Refresh rates every hour
    retry: shouldRetryCurrencyQuery,
    staleTime: staleTimes.currency,
    throwOnError: false,
  });

  useEffect(() => {
    if (query.data) {
      try {
        // Validate the response
        const validated = UPDATE_EXCHANGE_RATES_RESPONSE_SCHEMA.parse(query.data);
        updateAllExchangeRates(validated.rates, validated.timestamp);
      } catch (error) {
        recordClientErrorOnActiveSpan(
          error instanceof Error ? error : new Error("Invalid exchange rate data"),
          { queryKey: "currency.rates", source: "useFetchExchangeRates" }
        );
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
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  const query = useQuery<{ rate: number; timestamp: string }, AppError>({
    enabled: !!targetCurrency && targetCurrency !== baseCurrency,
    queryFn: async () => {
      try {
        return await makeAuthenticatedRequest<{ rate: number; timestamp: string }>(
          `/api/currencies/rates/${targetCurrency}`
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey: queryKeys.currency.rate(targetCurrency),
    retry: shouldRetryCurrencyQuery,
    staleTime: staleTimes.currency,
    throwOnError: false,
  });

  useEffect(() => {
    if (query.data) {
      updateExchangeRate(targetCurrency, query.data.rate, query.data.timestamp);
    }
  }, [query.data, targetCurrency, updateExchangeRate]);

  return query;
}
