import type { Currency, ExchangeRate } from "@/types/currency";
import { act } from "@testing-library/react";
import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { vi } from "vitest";
import { useCurrencyStore } from "../currency-store";

// Mock the store to avoid persistence issues in tests
vi.mock("zustand/middleware", () => ({
  persist: (fn) => fn,
}));

describe("useCurrencyStore", () => {
  // Clear the store before each test
  beforeEach(() => {
    act(() => {
      useCurrencyStore.setState({
        currencies: {
          USD: {
            code: "USD",
            symbol: "$",
            name: "US Dollar",
            decimals: 2,
            flag: "🇺🇸",
          },
          EUR: {
            code: "EUR",
            symbol: "€",
            name: "Euro",
            decimals: 2,
            flag: "🇪🇺",
          },
          GBP: {
            code: "GBP",
            symbol: "£",
            name: "British Pound",
            decimals: 2,
            flag: "🇬🇧",
          },
        },
        baseCurrency: "USD",
        exchangeRates: {},
        favoriteCurrencies: ["USD", "EUR"],
        lastUpdated: null,
      });
    });
  });

  describe("Currency Management", () => {
    it("initializes with default values", () => {
      const { result } = renderHook(() => useCurrencyStore());

      expect(result.current.baseCurrency).toBe("USD");
      expect(Object.keys(result.current.currencies)).toContain("USD");
      expect(Object.keys(result.current.currencies)).toContain("EUR");
      expect(Object.keys(result.current.currencies)).toContain("GBP");
      expect(result.current.exchangeRates).toEqual({});
      expect(result.current.favoriteCurrencies).toEqual(["USD", "EUR"]);
      expect(result.current.lastUpdated).toBeNull();
    });

    it("adds a new currency", () => {
      const { result } = renderHook(() => useCurrencyStore());

      const newCurrency: Currency = {
        code: "JPY",
        symbol: "¥",
        name: "Japanese Yen",
        decimals: 0,
        flag: "🇯🇵",
      };

      act(() => {
        result.current.addCurrency(newCurrency);
      });

      expect(result.current.currencies["JPY"]).toEqual(newCurrency);
    });

    it("removes a currency", () => {
      const { result } = renderHook(() => useCurrencyStore());

      act(() => {
        result.current.removeCurrency("GBP");
      });

      expect(result.current.currencies["GBP"]).toBeUndefined();
    });

    it("does not remove the base currency", () => {
      const { result } = renderHook(() => useCurrencyStore());

      act(() => {
        result.current.removeCurrency("USD");
      });

      expect(result.current.currencies["USD"]).toBeDefined();
    });

    it("sets the base currency", () => {
      const { result } = renderHook(() => useCurrencyStore());

      // Add exchange rates first
      act(() => {
        result.current.updateExchangeRate("EUR", 0.85);
        result.current.updateExchangeRate("GBP", 0.75);
      });

      // Change base currency from USD to EUR
      act(() => {
        result.current.setBaseCurrency("EUR");
      });

      expect(result.current.baseCurrency).toBe("EUR");

      // Exchange rates should be recalculated
      expect(result.current.exchangeRates["USD"]).toBeDefined();
      expect(result.current.exchangeRates["USD"]?.rate).toBeCloseTo(1 / 0.85);
      expect(result.current.exchangeRates["GBP"]?.rate).toBeCloseTo(0.75 / 0.85);
    });
  });

  describe("Exchange Rate Management", () => {
    it("updates an exchange rate", () => {
      const { result } = renderHook(() => useCurrencyStore());

      act(() => {
        result.current.updateExchangeRate("EUR", 0.85);
      });

      expect(result.current.exchangeRates["EUR"]).toBeDefined();
      expect(result.current.exchangeRates["EUR"]?.rate).toBe(0.85);
      expect(result.current.exchangeRates["EUR"]?.baseCurrency).toBe("USD");
      expect(result.current.exchangeRates["EUR"]?.targetCurrency).toBe("EUR");
      expect(result.current.lastUpdated).not.toBeNull();
    });

    it("does not allow setting an exchange rate for the base currency", () => {
      const { result } = renderHook(() => useCurrencyStore());

      act(() => {
        result.current.updateExchangeRate("USD", 1.0);
      });

      expect(result.current.exchangeRates["USD"]).toBeUndefined();
    });

    it("updates all exchange rates at once", () => {
      const { result } = renderHook(() => useCurrencyStore());

      const rates = {
        EUR: 0.85,
        GBP: 0.75,
        JPY: 110.25,
      };

      act(() => {
        result.current.updateAllExchangeRates(rates);
      });

      expect(result.current.exchangeRates["EUR"]?.rate).toBe(0.85);
      expect(result.current.exchangeRates["GBP"]?.rate).toBe(0.75);
      expect(result.current.exchangeRates["JPY"]?.rate).toBe(110.25);
      expect(result.current.lastUpdated).not.toBeNull();
    });
  });

  describe("Favorites Management", () => {
    it("adds a currency to favorites", () => {
      const { result } = renderHook(() => useCurrencyStore());

      act(() => {
        result.current.addFavoriteCurrency("GBP");
      });

      expect(result.current.favoriteCurrencies).toContain("GBP");
      expect(result.current.favoriteCurrencies.length).toBe(3);
    });

    it("does not add a non-existent currency to favorites", () => {
      const { result } = renderHook(() => useCurrencyStore());

      act(() => {
        result.current.addFavoriteCurrency("XYZ");
      });

      expect(result.current.favoriteCurrencies).not.toContain("XYZ");
      expect(result.current.favoriteCurrencies.length).toBe(2);
    });

    it("does not add a duplicate to favorites", () => {
      const { result } = renderHook(() => useCurrencyStore());

      act(() => {
        result.current.addFavoriteCurrency("USD");
      });

      expect(result.current.favoriteCurrencies).toContain("USD");
      expect(result.current.favoriteCurrencies.length).toBe(2); // No change
    });

    it("removes a currency from favorites", () => {
      const { result } = renderHook(() => useCurrencyStore());

      act(() => {
        result.current.removeFavoriteCurrency("EUR");
      });

      expect(result.current.favoriteCurrencies).not.toContain("EUR");
      expect(result.current.favoriteCurrencies.length).toBe(1);
    });
  });

  describe("Conversion Functions", () => {
    beforeEach(() => {
      act(() => {
        useCurrencyStore.setState({
          currencies: {
            USD: {
              code: "USD",
              symbol: "$",
              name: "US Dollar",
              decimals: 2,
              flag: "🇺🇸",
            },
            EUR: {
              code: "EUR",
              symbol: "€",
              name: "Euro",
              decimals: 2,
              flag: "🇪🇺",
            },
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
          },
          baseCurrency: "USD",
          exchangeRates: {
            EUR: {
              baseCurrency: "USD",
              targetCurrency: "EUR",
              rate: 0.85,
              timestamp: "2025-05-20T12:00:00Z",
            },
            GBP: {
              baseCurrency: "USD",
              targetCurrency: "GBP",
              rate: 0.75,
              timestamp: "2025-05-20T12:00:00Z",
            },
            JPY: {
              baseCurrency: "USD",
              targetCurrency: "JPY",
              rate: 110.0,
              timestamp: "2025-05-20T12:00:00Z",
            },
          },
          favoriteCurrencies: ["USD", "EUR", "GBP"],
          lastUpdated: "2025-05-20T12:00:00Z",
        });
      });
    });

    it("converts from base currency to another currency", () => {
      const { result } = renderHook(() => useCurrencyStore());

      const conversion = result.current.convertAmount(100, "USD", "EUR");

      expect(conversion).not.toBeNull();
      expect(conversion?.fromAmount).toBe(100);
      expect(conversion?.fromCurrency).toBe("USD");
      expect(conversion?.toAmount).toBe(85);
      expect(conversion?.toCurrency).toBe("EUR");
      expect(conversion?.rate).toBe(0.85);
    });

    it("converts from another currency to base currency", () => {
      const { result } = renderHook(() => useCurrencyStore());

      const conversion = result.current.convertAmount(100, "EUR", "USD");

      expect(conversion).not.toBeNull();
      expect(conversion?.fromAmount).toBe(100);
      expect(conversion?.fromCurrency).toBe("EUR");
      expect(conversion?.toAmount).toBeCloseTo(117.65, 2);
      expect(conversion?.toCurrency).toBe("USD");
      expect(conversion?.rate).toBeCloseTo(1.18, 2);
    });

    it("converts between two non-base currencies", () => {
      const { result } = renderHook(() => useCurrencyStore());

      const conversion = result.current.convertAmount(100, "EUR", "GBP");

      expect(conversion).not.toBeNull();
      expect(conversion?.fromAmount).toBe(100);
      expect(conversion?.fromCurrency).toBe("EUR");
      expect(conversion?.toAmount).toBeCloseTo(88.24, 2);
      expect(conversion?.toCurrency).toBe("GBP");
      expect(conversion?.rate).toBeCloseTo(0.88, 2);
    });

    it("handles the same currency (no conversion needed)", () => {
      const { result } = renderHook(() => useCurrencyStore());

      const conversion = result.current.convertAmount(100, "USD", "USD");

      expect(conversion).not.toBeNull();
      expect(conversion?.fromAmount).toBe(100);
      expect(conversion?.toAmount).toBe(100);
      expect(conversion?.rate).toBe(1);
    });

    it("returns null for unknown currency", () => {
      const { result } = renderHook(() => useCurrencyStore());

      const conversion = result.current.convertAmount(100, "XYZ", "USD");

      expect(conversion).toBeNull();
    });
  });

  describe("Utility Functions", () => {
    it("formats amount with currency", () => {
      const { result } = renderHook(() => useCurrencyStore());

      const formatted = result.current.formatAmountWithCurrency(1234.56, "USD");

      // Exact format depends on the browser locale, but should have $ and the amount
      expect(formatted).toContain("$");
      expect(formatted).toContain("1,234.56");
    });

    it("formats JPY without decimal places", () => {
      const { result } = renderHook(() => useCurrencyStore());

      // Add JPY first
      act(() => {
        result.current.addCurrency({
          code: "JPY",
          symbol: "¥",
          name: "Japanese Yen",
          decimals: 0,
          flag: "🇯🇵",
        });
      });

      const formatted = result.current.formatAmountWithCurrency(1234, "JPY");

      // JPY should not have decimal places
      expect(formatted).toContain("¥");
      expect(formatted).toContain("1,234");
      expect(formatted).not.toContain(".");
    });

    it("gets recent currency pairs", () => {
      const { result } = renderHook(() => useCurrencyStore());

      const pairs = result.current.getRecentCurrencyPairs();

      expect(pairs.length).toBe(1); // USD to EUR
      expect(pairs[0].fromCurrency).toBe("USD");
      expect(pairs[0].toCurrency).toBe("EUR");
    });

    it("gets popular currencies", () => {
      const { result } = renderHook(() => useCurrencyStore());

      const currencies = result.current.getPopularCurrencies();

      expect(currencies.length).toBe(2);
      expect(currencies[0].code).toBe("USD");
      expect(currencies[1].code).toBe("EUR");
    });

    it("gets currency by code", () => {
      const { result } = renderHook(() => useCurrencyStore());

      const currency = result.current.getCurrencyByCode("USD");

      expect(currency).toBeDefined();
      expect(currency?.code).toBe("USD");
      expect(currency?.symbol).toBe("$");
    });

    it("returns undefined for unknown currency code", () => {
      const { result } = renderHook(() => useCurrencyStore());

      const currency = result.current.getCurrencyByCode("XYZ");

      expect(currency).toBeUndefined();
    });
  });
});
