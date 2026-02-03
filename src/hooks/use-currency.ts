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
import { useCallback, useEffect, useMemo } from "react";
import { useShallow } from "zustand/react/shallow";
import { useCurrencyStore } from "@/features/shared/store/currency-store";
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";
import { type AppError, handleApiError, isApiError } from "@/lib/api/error-types";
import { keys } from "@/lib/keys";
import { staleTimes } from "@/lib/query/config";
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
 *
 * @returns Currency state slices used by consumers.
 */
export function useCurrency() {
  const { baseCurrency, currencies, exchangeRates, favoriteCurrencies, lastUpdated } =
    useCurrencyStore(
      useShallow((state) => ({
        baseCurrency: state.baseCurrency,
        currencies: state.currencies,
        exchangeRates: state.exchangeRates,
        favoriteCurrencies: state.favoriteCurrencies,
        lastUpdated: state.lastUpdated,
      }))
    );

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
 *
 * @returns Currency management action handlers.
 */
export function useCurrencyActions() {
  const {
    addCurrency,
    addFavoriteCurrency,
    removeCurrency,
    removeFavoriteCurrency,
    setBaseCurrency,
  } = useCurrencyStore(
    useShallow((state) => ({
      addCurrency: state.addCurrency,
      addFavoriteCurrency: state.addFavoriteCurrency,
      removeCurrency: state.removeCurrency,
      removeFavoriteCurrency: state.removeFavoriteCurrency,
      setBaseCurrency: state.setBaseCurrency,
    }))
  );

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
 *
 * @returns Exchange rate state and update actions.
 */
export function useExchangeRates() {
  const {
    baseCurrency,
    exchangeRates,
    lastUpdated,
    updateExchangeRate,
    updateAllExchangeRates,
  } = useCurrencyStore(
    useShallow((state) => ({
      baseCurrency: state.baseCurrency,
      exchangeRates: state.exchangeRates,
      lastUpdated: state.lastUpdated,
      updateAllExchangeRates: state.updateAllExchangeRates,
      updateExchangeRate: state.updateExchangeRate,
    }))
  );

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
 *
 * @returns Conversion helpers for amounts and rates.
 */
export function useCurrencyConverter() {
  const { convertAmount, formatAmountWithCurrency } = useCurrencyStore(
    useShallow((state) => ({
      convertAmount: state.convertAmount,
      formatAmountWithCurrency: state.formatAmountWithCurrency,
    }))
  );

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
 *
 * @returns Currency data helpers plus popular and recent selections.
 */
export function useCurrencyData() {
  const { getCurrencyByCode, getPopularCurrencies, getRecentCurrencyPairs } =
    useCurrencyStore(
      useShallow((state) => ({
        getCurrencyByCode: state.getCurrencyByCode,
        getPopularCurrencies: state.getPopularCurrencies,
        getRecentCurrencyPairs: state.getRecentCurrencyPairs,
      }))
    );

  const popularCurrencies = useMemo(
    () => getPopularCurrencies(),
    [getPopularCurrencies]
  );
  const recentPairs = useMemo(() => getRecentCurrencyPairs(), [getRecentCurrencyPairs]);

  return {
    getCurrencyByCode,
    popularCurrencies,
    recentPairs,
  };
}

/**
 * Hook for fetching exchange rates from API.
 *
 * @returns React Query result for the exchange rates fetch.
 */
export function useFetchExchangeRates() {
  const updateAllExchangeRates = useCurrencyStore(
    (state) => state.updateAllExchangeRates
  );
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
    queryKey: keys.currency.rates(),
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
 * @returns React Query result for the requested exchange rate.
 */
export function useFetchExchangeRate(targetCurrency: CurrencyCode) {
  const { baseCurrency, updateExchangeRate } = useCurrencyStore(
    useShallow((state) => ({
      baseCurrency: state.baseCurrency,
      updateExchangeRate: state.updateExchangeRate,
    }))
  );
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
    queryKey: keys.currency.rate(targetCurrency),
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
