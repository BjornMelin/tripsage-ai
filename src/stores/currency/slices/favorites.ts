/**
 * @fileoverview Favorites slice for the currency store.
 */

"use client";

import type { StateCreator } from "zustand";
import type { CurrencyStore } from "../../currency-store";
import { DEFAULT_FAVORITE_CURRENCIES, isCurrencyCode } from "../shared";
import type { StoreLogger } from "../types";

type CurrencyFavoritesSlice = Pick<
  CurrencyStore,
  "favoriteCurrencies" | "addFavoriteCurrency" | "removeFavoriteCurrency"
>;

export const createCurrencyFavoritesSlice =
  (logger: StoreLogger): StateCreator<CurrencyStore, [], [], CurrencyFavoritesSlice> =>
  (set) => ({
    addFavoriteCurrency: (code) =>
      set((state) => {
        if (!isCurrencyCode(code)) {
          logger.error("Invalid currency code", { code });
          return state;
        }

        if (!state.currencies[code] || state.favoriteCurrencies.includes(code)) {
          return state;
        }

        return {
          favoriteCurrencies: [...state.favoriteCurrencies, code],
        };
      }),
    favoriteCurrencies: [...DEFAULT_FAVORITE_CURRENCIES],
    removeFavoriteCurrency: (code) =>
      set((state) => {
        if (!isCurrencyCode(code)) {
          logger.error("Invalid currency code", { code });
          return state;
        }

        if (!state.currencies[code]) {
          logger.warn("Favorite removal skipped for unknown currency", { code });
          return state;
        }

        return {
          favoriteCurrencies: state.favoriteCurrencies.filter(
            (currencyCode) => currencyCode !== code
          ),
        };
      }),
  });
