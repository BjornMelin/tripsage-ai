import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  CONVERSION_RESULT_SCHEMA,
  type ConversionResult,
  CURRENCY_CODE_SCHEMA,
  CURRENCY_PAIR_SCHEMA,
  CURRENCY_SCHEMA,
  type Currency,
  type CurrencyCode,
  type CurrencyPair,
  type CurrencyState,
  EXCHANGE_RATE_SCHEMA,
  type ExchangeRate,
} from "@/types/currency";

// Common currencies with symbols and decimal places
// ISO 4217 defines currency codes in UPPER_CASE (international standard)
const COMMON_CURRENCIES: Record<CurrencyCode, Currency> = {
  AUD: {
    code: "AUD",
    decimals: 2,
    flag: "🇦🇺",
    name: "Australian Dollar",
    symbol: "A$",
  },
  CAD: {
    code: "CAD",
    decimals: 2,
    flag: "🇨🇦",
    name: "Canadian Dollar",
    symbol: "C$",
  },
  CHF: {
    code: "CHF",
    decimals: 2,
    flag: "🇨🇭",
    name: "Swiss Franc",
    symbol: "Fr",
  },
  CNY: {
    code: "CNY",
    decimals: 2,
    flag: "🇨🇳",
    name: "Chinese Yuan",
    symbol: "¥",
  },
  EUR: { code: "EUR", decimals: 2, flag: "🇪🇺", name: "Euro", symbol: "€" },
  GBP: {
    code: "GBP",
    decimals: 2,
    flag: "🇬🇧",
    name: "British Pound",
    symbol: "£",
  },
  INR: {
    code: "INR",
    decimals: 2,
    flag: "🇮🇳",
    name: "Indian Rupee",
    symbol: "₹",
  },
  JPY: {
    code: "JPY",
    decimals: 0,
    flag: "🇯🇵",
    name: "Japanese Yen",
    symbol: "¥",
  },
  MXN: {
    code: "MXN",
    decimals: 2,
    flag: "🇲🇽",
    name: "Mexican Peso",
    symbol: "$",
  },
  USD: { code: "USD", decimals: 2, flag: "🇺🇸", name: "US Dollar", symbol: "$" },
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

  // Additional features
  getRecentCurrencyPairs: () => CurrencyPair[];
  getPopularCurrencies: () => Currency[];
  getCurrencyByCode: (code: string) => Currency | undefined;
  formatAmountWithCurrency: (amount: number, currencyCode: string) => string;
}

// Helper functions
const GET_CURRENT_TIMESTAMP = () => new Date().toISOString();

// Validate the currency code
const VALIDATE_CURRENCY_CODE = (code: unknown): code is CurrencyCode => {
  return CURRENCY_CODE_SCHEMA.safeParse(code).success;
};

// Validate the currency object
// const validateCurrency = (currency: unknown): currency is Currency => {
//   return CurrencySchema.safeParse(currency).success;
// }; // Future validation

export const useCurrencyStore = create<CurrencyStore>()(
  persist(
    (set, get) => ({
      addCurrency: (currency) => {
        // Validate the currency against the schema
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
        console.error("Invalid currency data:", result.error);
        return false;
      },

      // Favorites management
      addFavoriteCurrency: (code) =>
        set((state) => {
          // Validate the currency code
          if (!VALIDATE_CURRENCY_CODE(code)) {
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
      baseCurrency: "USD",

      // Conversion utilities
      convertAmount: (amount, fromCurrency, toCurrency) => {
        const state = get();

        // Validate inputs
        if (
          typeof amount !== "number" ||
          !VALIDATE_CURRENCY_CODE(fromCurrency) ||
          !VALIDATE_CURRENCY_CODE(toCurrency)
        ) {
          console.error("Invalid conversion parameters");
          return null;
        }

        // Same currency, no conversion needed
        if (fromCurrency === toCurrency) {
          const result = {
            fromAmount: amount,
            fromCurrency,
            rate: 1,
            timestamp: GET_CURRENT_TIMESTAMP(),
            toAmount: amount,
            toCurrency,
          };

          return CONVERSION_RESULT_SCHEMA.parse(result);
        }

        // Convert from base currency
        if (fromCurrency === state.baseCurrency) {
          const exchangeRate = state.exchangeRates[toCurrency];
          if (!exchangeRate) return null;

          const convertedAmount = amount * exchangeRate.rate;

          const result = {
            fromAmount: amount,
            fromCurrency,
            rate: exchangeRate.rate,
            timestamp: exchangeRate.timestamp,
            toAmount: convertedAmount,
            toCurrency,
          };

          return CONVERSION_RESULT_SCHEMA.parse(result);
        }

        // Convert to base currency
        if (toCurrency === state.baseCurrency) {
          const exchangeRate = state.exchangeRates[fromCurrency];
          if (!exchangeRate) return null;

          const convertedAmount = amount / exchangeRate.rate;

          const result = {
            fromAmount: amount,
            fromCurrency,
            rate: 1 / exchangeRate.rate,
            timestamp: exchangeRate.timestamp,
            toAmount: convertedAmount,
            toCurrency,
          };

          return CONVERSION_RESULT_SCHEMA.parse(result);
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
          rate: effectiveRate,
          timestamp: GET_CURRENT_TIMESTAMP(),
          toAmount: convertedAmount,
          toCurrency,
        };

        return CONVERSION_RESULT_SCHEMA.parse(result);
      },
      // Initial state
      currencies: COMMON_CURRENCIES,
      exchangeRates: {},
      favoriteCurrencies: ["USD", "EUR", "GBP"],

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
          console.error(`Error formatting currency: ${error}`);
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

      getPopularCurrencies: () => {
        const state = get();
        return state.favoriteCurrencies
          .map((code) => state.currencies[code])
          .filter(Boolean);
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

            if (CURRENCY_PAIR_SCHEMA.safeParse(pair).success) {
              pairs.push(pair);
            }
          }
        });

        return pairs;
      },
      lastUpdated: null,

      removeCurrency: (code) =>
        set((state) => {
          // Validate the currency code
          if (!VALIDATE_CURRENCY_CODE(code)) {
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

      removeFavoriteCurrency: (code) =>
        set((state) => {
          // Validate the currency code
          if (!VALIDATE_CURRENCY_CODE(code)) {
            console.error(`Invalid currency code: ${code}`);
            return state;
          }

          return {
            favoriteCurrencies: state.favoriteCurrencies.filter(
              (currencyCode) => currencyCode !== code
            ),
          };
        }),

      // Currency management
      setBaseCurrency: (currency) =>
        set((state) => {
          // Validate the currency code
          if (!VALIDATE_CURRENCY_CODE(currency)) {
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
              rate: newRate,
              targetCurrency: currencyCode,
              timestamp: GET_CURRENT_TIMESTAMP(),
            };

            if (EXCHANGE_RATE_SCHEMA.safeParse(newExchangeRate).success) {
              newExchangeRates[currencyCode] = newExchangeRate;
            }
          });

          // Add the old base currency to the exchange rates
          const oldBaseExchangeRate = {
            baseCurrency: currency,
            rate: 1 / oldBaseRate,
            targetCurrency: oldBaseCurrency,
            timestamp: GET_CURRENT_TIMESTAMP(),
          };

          if (EXCHANGE_RATE_SCHEMA.safeParse(oldBaseExchangeRate).success) {
            newExchangeRates[oldBaseCurrency] = oldBaseExchangeRate;
          }

          return {
            baseCurrency: currency,
            exchangeRates: newExchangeRates,
            lastUpdated: GET_CURRENT_TIMESTAMP(),
          };
        }),

      updateAllExchangeRates: (rates, timestamp = GET_CURRENT_TIMESTAMP()) =>
        set((state) => {
          const newExchangeRates: Record<CurrencyCode, ExchangeRate> = {};

          Object.entries(rates).forEach(([currencyCode, rate]) => {
            // Skip if it's the base currency or invalid code
            if (
              currencyCode === state.baseCurrency ||
              !VALIDATE_CURRENCY_CODE(currencyCode) ||
              typeof rate !== "number" ||
              rate <= 0
            ) {
              return;
            }

            // Create and validate the new exchange rate
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

      // Exchange rate management
      updateExchangeRate: (targetCurrency, rate, timestamp = GET_CURRENT_TIMESTAMP()) =>
        set((state) => {
          // Validate the currency code
          if (!VALIDATE_CURRENCY_CODE(targetCurrency)) {
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
            rate,
            targetCurrency,
            timestamp,
          };

          const result = EXCHANGE_RATE_SCHEMA.safeParse(newExchangeRate);
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
