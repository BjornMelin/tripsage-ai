import {
  type ConversionResult,
  ConversionResultSchema,
  type Currency,
  type CurrencyCode,
  CurrencyCodeSchema,
  type CurrencyPair,
  CurrencyPairSchema,
  CurrencySchema,
  type CurrencyState,
  type ExchangeRate,
  ExchangeRateSchema,
} from "@/types/currency";
import { create } from "zustand";
import { persist } from "zustand/middleware";

// Common currencies with symbols and decimal places
const COMMON_CURRENCIES: Record<CurrencyCode, Currency> = {
  USD: { code: "USD", symbol: "$", name: "US Dollar", decimals: 2, flag: "🇺🇸" },
  EUR: { code: "EUR", symbol: "€", name: "Euro", decimals: 2, flag: "🇪🇺" },
  GBP: {
    code: "GBP",
    symbol: "£",
    name: "British Pound",
    decimals: 2,
    flag: "🇬🇧",
  },
  JPY: {
    code: "JPY",
    symbol: "¥",
    name: "Japanese Yen",
    decimals: 0,
    flag: "🇯🇵",
  },
  CAD: {
    code: "CAD",
    symbol: "C$",
    name: "Canadian Dollar",
    decimals: 2,
    flag: "🇨🇦",
  },
  AUD: {
    code: "AUD",
    symbol: "A$",
    name: "Australian Dollar",
    decimals: 2,
    flag: "🇦🇺",
  },
  CHF: {
    code: "CHF",
    symbol: "Fr",
    name: "Swiss Franc",
    decimals: 2,
    flag: "🇨🇭",
  },
  CNY: {
    code: "CNY",
    symbol: "¥",
    name: "Chinese Yuan",
    decimals: 2,
    flag: "🇨🇳",
  },
  INR: {
    code: "INR",
    symbol: "₹",
    name: "Indian Rupee",
    decimals: 2,
    flag: "🇮🇳",
  },
  MXN: {
    code: "MXN",
    symbol: "$",
    name: "Mexican Peso",
    decimals: 2,
    flag: "🇲🇽",
  },
};

interface CurrencyStore extends CurrencyState {
  // Currency management
  setBaseCurrency: (currency: CurrencyCode) => void;
  addCurrency: (currency: unknown) => boolean;
  removeCurrency: (code: CurrencyCode) => void;

  // Exchange rate management
  updateExchangeRate: (
    targetCurrency: CurrencyCode,
    rate: number,
    timestamp?: string
  ) => void;
  updateAllExchangeRates: (rates: Record<string, number>, timestamp?: string) => void;

  // Favorites management
  addFavoriteCurrency: (code: CurrencyCode) => void;
  removeFavoriteCurrency: (code: CurrencyCode) => void;

  // Conversion utilities
  convertAmount: (
    amount: number,
    fromCurrency: CurrencyCode,
    toCurrency: CurrencyCode
  ) => ConversionResult | null;

  // Advanced features
  getRecentCurrencyPairs: () => CurrencyPair[];
  getPopularCurrencies: () => Currency[];
  getCurrencyByCode: (code: string) => Currency | undefined;
  formatAmountWithCurrency: (amount: number, currencyCode: string) => string;
}

// Helper functions
const getCurrentTimestamp = () => new Date().toISOString();

// Validate the currency code
const validateCurrencyCode = (code: unknown): code is CurrencyCode => {
  return CurrencyCodeSchema.safeParse(code).success;
};

// Validate the currency object
const _validateCurrency = (currency: unknown): currency is Currency => {
  return CurrencySchema.safeParse(currency).success;
};

export const useCurrencyStore = create<CurrencyStore>()(
  persist(
    (set, get) => ({
      // Initial state
      currencies: COMMON_CURRENCIES,
      baseCurrency: "USD",
      exchangeRates: {},
      favoriteCurrencies: ["USD", "EUR", "GBP"],
      lastUpdated: null,

      // Currency management
      setBaseCurrency: (currency) =>
        set((state) => {
          // Validate the currency code
          if (!validateCurrencyCode(currency)) {
            console.error(`Invalid currency code: ${currency}`);
            return state;
          }

          // Don't update if the currency is already the base or doesn't exist
          if (currency === state.baseCurrency || !state.currencies[currency]) {
            return state;
          }

          // When changing base currency, we need to recalculate all exchange rates
          const oldBaseCurrency = state.baseCurrency;
          const oldBaseRate = state.exchangeRates[currency]?.rate || 1;

          // Calculate new exchange rates relative to the new base currency
          const newExchangeRates: Record<CurrencyCode, ExchangeRate> = {};

          Object.keys(state.exchangeRates).forEach((currencyCode) => {
            if (currencyCode === currency) return; // Skip the new base currency

            const oldRate = state.exchangeRates[currencyCode]?.rate || 1;
            const newRate = oldRate / oldBaseRate;

            // Create and validate the new exchange rate
            const newExchangeRate = {
              baseCurrency: currency,
              targetCurrency: currencyCode,
              rate: newRate,
              timestamp: getCurrentTimestamp(),
            };

            if (ExchangeRateSchema.safeParse(newExchangeRate).success) {
              newExchangeRates[currencyCode] = newExchangeRate;
            }
          });

          // Add the old base currency to the exchange rates
          const oldBaseExchangeRate = {
            baseCurrency: currency,
            targetCurrency: oldBaseCurrency,
            rate: 1 / oldBaseRate,
            timestamp: getCurrentTimestamp(),
          };

          if (ExchangeRateSchema.safeParse(oldBaseExchangeRate).success) {
            newExchangeRates[oldBaseCurrency] = oldBaseExchangeRate;
          }

          return {
            baseCurrency: currency,
            exchangeRates: newExchangeRates,
            lastUpdated: getCurrentTimestamp(),
          };
        }),

      addCurrency: (currency) => {
        // Validate the currency against the schema
        const result = CurrencySchema.safeParse(currency);
        if (result.success) {
          set((state) => ({
            currencies: {
              ...state.currencies,
              [result.data.code]: result.data,
            },
          }));
          return true;
        }
        console.error("Invalid currency data:", result.error);
        return false;
      },

      removeCurrency: (code) =>
        set((state) => {
          // Validate the currency code
          if (!validateCurrencyCode(code)) {
            console.error(`Invalid currency code: ${code}`);
            return state;
          }

          // Don't remove the base currency
          if (code === state.baseCurrency) return state;

          // Create new state objects without the currency
          const newCurrencies = { ...state.currencies };
          const newExchangeRates = { ...state.exchangeRates };
          const newFavoriteCurrencies = state.favoriteCurrencies.filter(
            (c) => c !== code
          );

          // Remove the currency from all state
          delete newCurrencies[code];
          delete newExchangeRates[code];

          return {
            currencies: newCurrencies,
            exchangeRates: newExchangeRates,
            favoriteCurrencies: newFavoriteCurrencies,
          };
        }),

      // Exchange rate management
      updateExchangeRate: (targetCurrency, rate, timestamp = getCurrentTimestamp()) =>
        set((state) => {
          // Validate the currency code
          if (!validateCurrencyCode(targetCurrency)) {
            console.error(`Invalid currency code: ${targetCurrency}`);
            return state;
          }

          // Validate the rate
          if (typeof rate !== "number" || rate <= 0) {
            console.error(`Invalid exchange rate: ${rate}`);
            return state;
          }

          if (targetCurrency === state.baseCurrency) return state; // Can't set exchange rate for base currency

          // Create and validate the new exchange rate
          const newExchangeRate = {
            baseCurrency: state.baseCurrency,
            targetCurrency,
            rate,
            timestamp,
          };

          const result = ExchangeRateSchema.safeParse(newExchangeRate);
          if (!result.success) {
            console.error("Invalid exchange rate data:", result.error);
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

      updateAllExchangeRates: (rates, timestamp = getCurrentTimestamp()) =>
        set((state) => {
          const newExchangeRates: Record<CurrencyCode, ExchangeRate> = {};

          Object.entries(rates).forEach(([currencyCode, rate]) => {
            // Skip if it's the base currency or invalid code
            if (
              currencyCode === state.baseCurrency ||
              !validateCurrencyCode(currencyCode) ||
              typeof rate !== "number" ||
              rate <= 0
            ) {
              return;
            }

            // Create and validate the new exchange rate
            const newExchangeRate = {
              baseCurrency: state.baseCurrency,
              targetCurrency: currencyCode,
              rate,
              timestamp,
            };

            const result = ExchangeRateSchema.safeParse(newExchangeRate);
            if (result.success) {
              newExchangeRates[currencyCode] = newExchangeRate;
            }
          });

          return {
            exchangeRates: newExchangeRates,
            lastUpdated: timestamp,
          };
        }),

      // Favorites management
      addFavoriteCurrency: (code) =>
        set((state) => {
          // Validate the currency code
          if (!validateCurrencyCode(code)) {
            console.error(`Invalid currency code: ${code}`);
            return state;
          }

          if (!state.currencies[code] || state.favoriteCurrencies.includes(code)) {
            return state;
          }

          return {
            favoriteCurrencies: [...state.favoriteCurrencies, code],
          };
        }),

      removeFavoriteCurrency: (code) =>
        set((state) => {
          // Validate the currency code
          if (!validateCurrencyCode(code)) {
            console.error(`Invalid currency code: ${code}`);
            return state;
          }

          return {
            favoriteCurrencies: state.favoriteCurrencies.filter(
              (currencyCode) => currencyCode !== code
            ),
          };
        }),

      // Conversion utilities
      convertAmount: (amount, fromCurrency, toCurrency) => {
        const state = get();

        // Validate inputs
        if (
          typeof amount !== "number" ||
          !validateCurrencyCode(fromCurrency) ||
          !validateCurrencyCode(toCurrency)
        ) {
          console.error("Invalid conversion parameters");
          return null;
        }

        // Same currency, no conversion needed
        if (fromCurrency === toCurrency) {
          const result = {
            fromAmount: amount,
            fromCurrency,
            toAmount: amount,
            toCurrency,
            rate: 1,
            timestamp: getCurrentTimestamp(),
          };

          return ConversionResultSchema.parse(result);
        }

        // Convert from base currency
        if (fromCurrency === state.baseCurrency) {
          const exchangeRate = state.exchangeRates[toCurrency];
          if (!exchangeRate) return null;

          const convertedAmount = amount * exchangeRate.rate;

          const result = {
            fromAmount: amount,
            fromCurrency,
            toAmount: convertedAmount,
            toCurrency,
            rate: exchangeRate.rate,
            timestamp: exchangeRate.timestamp,
          };

          return ConversionResultSchema.parse(result);
        }

        // Convert to base currency
        if (toCurrency === state.baseCurrency) {
          const exchangeRate = state.exchangeRates[fromCurrency];
          if (!exchangeRate) return null;

          const convertedAmount = amount / exchangeRate.rate;

          const result = {
            fromAmount: amount,
            fromCurrency,
            toAmount: convertedAmount,
            toCurrency,
            rate: 1 / exchangeRate.rate,
            timestamp: exchangeRate.timestamp,
          };

          return ConversionResultSchema.parse(result);
        }

        // Convert between two non-base currencies
        const fromExchangeRate = state.exchangeRates[fromCurrency];
        const toExchangeRate = state.exchangeRates[toCurrency];

        if (!fromExchangeRate || !toExchangeRate) return null;

        // Convert via the base currency
        const amountInBaseCurrency = amount / fromExchangeRate.rate;
        const convertedAmount = amountInBaseCurrency * toExchangeRate.rate;
        const effectiveRate = toExchangeRate.rate / fromExchangeRate.rate;

        const result = {
          fromAmount: amount,
          fromCurrency,
          toAmount: convertedAmount,
          toCurrency,
          rate: effectiveRate,
          timestamp: getCurrentTimestamp(),
        };

        return ConversionResultSchema.parse(result);
      },

      // Utility methods
      getRecentCurrencyPairs: () => {
        const state = get();
        const pairs: CurrencyPair[] = [];

        // Base currency to favorites
        state.favoriteCurrencies.forEach((code) => {
          if (code !== state.baseCurrency) {
            const pair = {
              fromCurrency: state.baseCurrency,
              toCurrency: code,
            };

            if (CurrencyPairSchema.safeParse(pair).success) {
              pairs.push(pair);
            }
          }
        });

        return pairs;
      },

      getPopularCurrencies: () => {
        const state = get();
        return state.favoriteCurrencies
          .map((code) => state.currencies[code])
          .filter(Boolean);
      },

      getCurrencyByCode: (code) => {
        const state = get();
        const result = CurrencyCodeSchema.safeParse(code);
        if (result.success) {
          return state.currencies[result.data];
        }
        return undefined;
      },

      formatAmountWithCurrency: (amount, currencyCode) => {
        const state = get();
        const result = CurrencyCodeSchema.safeParse(currencyCode);

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
            style: "currency",
            currency: code,
            minimumFractionDigits: currency.decimals,
            maximumFractionDigits: currency.decimals,
          }).format(amount);
        } catch (error) {
          console.error(`Error formatting currency: ${error}`);
          return `${amount} ${code}`;
        }
      },
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
  )
);
