import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useCurrencyStore } from "@/stores/currency-store";
import {
  useCurrency,
  useCurrencyActions,
  useCurrencyConverter,
  useCurrencyData,
  useExchangeRates,
} from "../use-currency";

// Mock the store to avoid persistence issues in tests
vi.mock("zustand/middleware", () => ({
  persist: (fn: any) => fn,
}));

// Mock API query hooks
vi.mock("@/hooks/use-api-query", () => ({
  useApiQuery: vi.fn().mockReturnValue({
    data: null,
    error: null,
    isLoading: false,
    refetch: vi.fn(),
  }),
}));

describe("Currency Hooks", () => {
  // Reset the store before each test
  beforeEach(() => {
    act(() => {
      useCurrencyStore.setState({
        baseCurrency: "USD",
        currencies: {
          EUR: {
            code: "EUR",
            decimals: 2,
            flag: "🇪🇺",
            name: "Euro",
            symbol: "€",
          },
          GBP: {
            code: "GBP",
            decimals: 2,
            flag: "🇬🇧",
            name: "British Pound",
            symbol: "£",
          },
          USD: {
            code: "USD",
            decimals: 2,
            flag: "🇺🇸",
            name: "US Dollar",
            symbol: "$",
          },
        },
        exchangeRates: {
          EUR: {
            baseCurrency: "USD",
            rate: 0.85,
            targetCurrency: "EUR",
            timestamp: "2025-05-20T12:00:00Z",
          },
          GBP: {
            baseCurrency: "USD",
            rate: 0.75,
            targetCurrency: "GBP",
            timestamp: "2025-05-20T12:00:00Z",
          },
        },
        favoriteCurrencies: ["USD", "EUR"],
        lastUpdated: "2025-05-20T12:00:00Z",
      });
    });
  });

  describe("useCurrency", () => {
    it("returns the current currency state", () => {
      const { result } = renderHook(() => useCurrency());

      expect(result.current.baseCurrency).toBe("USD");
      expect(Object.keys(result.current.currencies)).toContain("USD");
      expect(Object.keys(result.current.currencies)).toContain("EUR");
      expect(Object.keys(result.current.currencies)).toContain("GBP");
      expect(Object.keys(result.current.exchangeRates)).toContain("EUR");
      expect(Object.keys(result.current.exchangeRates)).toContain("GBP");
      expect(result.current.favoriteCurrencies).toEqual(["USD", "EUR"]);
      expect(result.current.lastUpdated).toBe("2025-05-20T12:00:00Z");
    });
  });

  describe("useCurrencyActions", () => {
    it("provides methods to modify currency state", () => {
      const { result } = renderHook(() => useCurrencyActions());

      // Check that all methods exist
      expect(typeof result.current.setBaseCurrency).toBe("function");
      expect(typeof result.current.addCurrency).toBe("function");
      expect(typeof result.current.removeCurrency).toBe("function");
      expect(typeof result.current.addFavoriteCurrency).toBe("function");
      expect(typeof result.current.removeFavoriteCurrency).toBe("function");
    });

    it("can change the base currency", () => {
      const { result } = renderHook(() => useCurrencyActions());

      act(() => {
        result.current.setBaseCurrency("EUR");
      });

      // Check that the base currency changed
      const newState = useCurrencyStore.getState();
      expect(newState.baseCurrency).toBe("EUR");

      // Exchange rates should be recalculated
      expect(newState.exchangeRates.USD).toBeDefined();
      expect(newState.exchangeRates.USD?.rate).toBeCloseTo(1 / 0.85);
    });

    it("can add a new currency", () => {
      const { result } = renderHook(() => useCurrencyActions());

      const newCurrency = {
        code: "JPY",
        decimals: 0,
        flag: "🇯🇵",
        name: "Japanese Yen",
        symbol: "¥",
      };

      act(() => {
        result.current.addCurrency(newCurrency);
      });

      // Check that the currency was added
      const newState = useCurrencyStore.getState();
      expect(newState.currencies.JPY).toEqual(newCurrency);
    });

    it("validates currency data before adding", () => {
      const { result } = renderHook(() => useCurrencyActions());

      const invalidCurrency = {
        code: "INVALID", // Invalid code (too long)
        decimals: 2,
        name: "Invalid Currency",
        symbol: "$",
      };

      let success;
      act(() => {
        success = result.current.addCurrency(invalidCurrency);
      });

      // Check that the currency was not added
      expect(success).toBe(false);
      const newState = useCurrencyStore.getState();
      expect(newState.currencies.INVALID).toBeUndefined();
    });
  });

  describe("useExchangeRates", () => {
    it("returns exchange rate state and methods", () => {
      const { result } = renderHook(() => useExchangeRates());

      expect(result.current.baseCurrency).toBe("USD");
      expect(Object.keys(result.current.exchangeRates)).toContain("EUR");
      expect(Object.keys(result.current.exchangeRates)).toContain("GBP");
      expect(result.current.lastUpdated).toBe("2025-05-20T12:00:00Z");
      expect(typeof result.current.updateExchangeRate).toBe("function");
      expect(typeof result.current.updateAllExchangeRates).toBe("function");
    });

    it("can update an exchange rate", () => {
      const { result } = renderHook(() => useExchangeRates());

      act(() => {
        result.current.updateExchangeRate("EUR", 0.9, "2025-05-21T12:00:00Z");
      });

      // Check that the rate was updated
      const newState = useCurrencyStore.getState();
      expect(newState.exchangeRates.EUR?.rate).toBe(0.9);
      expect(newState.exchangeRates.EUR?.timestamp).toBe("2025-05-21T12:00:00Z");
    });

    it("can update all exchange rates", () => {
      const { result } = renderHook(() => useExchangeRates());

      const newRates = {
        EUR: 0.9,
        GBP: 0.8,
        JPY: 110.0,
      };

      act(() => {
        result.current.updateAllExchangeRates(newRates, "2025-05-21T12:00:00Z");
      });

      // Check that rates were updated
      const newState = useCurrencyStore.getState();
      expect(newState.exchangeRates.EUR?.rate).toBe(0.9);
      expect(newState.exchangeRates.GBP?.rate).toBe(0.8);
      expect(newState.exchangeRates.JPY?.rate).toBe(110.0);
      expect(newState.lastUpdated).toBe("2025-05-21T12:00:00Z");
    });
  });

  describe("useCurrencyConverter", () => {
    it("provides conversion methods", () => {
      const { result } = renderHook(() => useCurrencyConverter());

      expect(typeof result.current.convert).toBe("function");
      expect(typeof result.current.format).toBe("function");
      expect(typeof result.current.getBestRate).toBe("function");
    });

    it("can convert from base currency", () => {
      const { result } = renderHook(() => useCurrencyConverter());

      const conversion = result.current.convert(100, "USD", "EUR");

      expect(conversion).not.toBeNull();
      expect(conversion?.fromAmount).toBe(100);
      expect(conversion?.toAmount).toBe(85);
      expect(conversion?.rate).toBe(0.85);
    });

    it("can convert to base currency", () => {
      const { result } = renderHook(() => useCurrencyConverter());

      const conversion = result.current.convert(100, "EUR", "USD");

      expect(conversion).not.toBeNull();
      expect(conversion?.fromAmount).toBe(100);
      expect(conversion?.toAmount).toBeCloseTo(117.65, 2);
      expect(conversion?.rate).toBeCloseTo(1.18, 2);
    });

    it("can convert between non-base currencies", () => {
      const { result } = renderHook(() => useCurrencyConverter());

      const conversion = result.current.convert(100, "EUR", "GBP");

      expect(conversion).not.toBeNull();
      expect(conversion?.fromAmount).toBe(100);
      expect(conversion?.toAmount).toBeCloseTo(88.24, 2);
      expect(conversion?.rate).toBeCloseTo(0.88, 2);
    });

    it("formats currency values", () => {
      const { result } = renderHook(() => useCurrencyConverter());

      const formatted = result.current.format(1234.56, "USD");

      // Exact format depends on the browser locale, but should have $ and the amount
      expect(formatted).toContain("$");
      expect(formatted).toContain("1,234.56");
    });

    it("returns best exchange rate", () => {
      const { result } = renderHook(() => useCurrencyConverter());

      const rate = result.current.getBestRate("USD", "EUR");

      expect(rate).toBe(0.85);
    });
  });

  describe("useCurrencyData", () => {
    it("returns currency pairs and popular currencies", () => {
      const { result } = renderHook(() => useCurrencyData());

      expect(result.current.recentPairs.length).toBe(1);
      expect(result.current.recentPairs[0]).toEqual({
        fromCurrency: "USD",
        toCurrency: "EUR",
      });

      expect(result.current.popularCurrencies.length).toBe(2);
      expect(result.current.popularCurrencies[0].code).toBe("USD");
      expect(result.current.popularCurrencies[1].code).toBe("EUR");
    });

    it("can get currency by code", () => {
      const { result } = renderHook(() => useCurrencyData());

      const currency = result.current.getCurrencyByCode("USD");

      expect(currency).toBeDefined();
      expect(currency?.code).toBe("USD");
      expect(currency?.symbol).toBe("$");
    });
  });
});
