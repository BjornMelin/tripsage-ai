/**
 * @fileoverview Shared currency store utilities and defaults.
 */

"use client";

import type { Currency } from "@schemas/currency";
import { CURRENCY_CODE_SCHEMA, type CurrencyCode } from "@schemas/shared/money";

export const isCurrencyCode = (code: unknown): code is CurrencyCode => {
  return CURRENCY_CODE_SCHEMA.safeParse(code).success;
};

// Common currencies with symbols and decimal places
// ISO 4217 defines currency codes in UPPER_CASE (international standard)
export const COMMON_CURRENCIES = new Map<CurrencyCode, Currency>([
  [
    "AUD",
    {
      code: "AUD",
      decimals: 2,
      flag: "🇦🇺",
      name: "Australian Dollar",
      symbol: "A$",
    },
  ],
  [
    "CAD",
    {
      code: "CAD",
      decimals: 2,
      flag: "🇨🇦",
      name: "Canadian Dollar",
      symbol: "C$",
    },
  ],
  [
    "CHF",
    {
      code: "CHF",
      decimals: 2,
      flag: "🇨🇭",
      name: "Swiss Franc",
      symbol: "Fr",
    },
  ],
  [
    "CNY",
    {
      code: "CNY",
      decimals: 2,
      flag: "🇨🇳",
      name: "Chinese Yuan",
      symbol: "¥",
    },
  ],
  ["EUR", { code: "EUR", decimals: 2, flag: "🇪🇺", name: "Euro", symbol: "€" }],
  [
    "GBP",
    {
      code: "GBP",
      decimals: 2,
      flag: "🇬🇧",
      name: "British Pound",
      symbol: "£",
    },
  ],
  [
    "INR",
    {
      code: "INR",
      decimals: 2,
      flag: "🇮🇳",
      name: "Indian Rupee",
      symbol: "₹",
    },
  ],
  [
    "JPY",
    {
      code: "JPY",
      decimals: 0,
      flag: "🇯🇵",
      name: "Japanese Yen",
      symbol: "¥",
    },
  ],
  [
    "MXN",
    {
      code: "MXN",
      decimals: 2,
      flag: "🇲🇽",
      name: "Mexican Peso",
      symbol: "$",
    },
  ],
  ["USD", { code: "USD", decimals: 2, flag: "🇺🇸", name: "US Dollar", symbol: "$" }],
]);

export const DEFAULT_CURRENCIES = Object.fromEntries(
  COMMON_CURRENCIES
) satisfies Record<string, Currency>;

export const DEFAULT_FAVORITE_CURRENCIES: CurrencyCode[] = ["USD", "EUR", "GBP"];
