/**
 * @fileoverview Currency management and exchange rate schemas.
 * Includes currency codes, metadata, exchange rates, conversion results, and store state.
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";

// ===== CORE SCHEMAS =====
// Core business logic schemas for currency management

/**
 * Zod schema for ISO 4217 currency codes (3-letter uppercase).
 * Validates currency code format and structure.
 */
export const CURRENCY_CODE_SCHEMA = z
  .string()
  .length(3)
  .regex(/^[A-Z]{3}$/, { error: "Currency code must be a valid 3-letter ISO code" });

/** TypeScript type for currency codes. */
export type CurrencyCode = z.infer<typeof CURRENCY_CODE_SCHEMA>;

/**
 * Zod schema for currency metadata and display information.
 * Validates currency details including code, name, symbol, and decimal places.
 */
export const CURRENCY_SCHEMA = z.object({
  code: CURRENCY_CODE_SCHEMA,
  decimals: z.number().int().min(0).max(10),
  flag: z.string().optional(),
  name: z.string().min(1),
  symbol: z.string().min(1),
});

/** TypeScript type for currency metadata. */
export type Currency = z.infer<typeof CURRENCY_SCHEMA>;

/**
 * Zod schema for currency exchange rate data.
 * Validates exchange rate information including base currency, target currency, rate, and timestamp.
 */
export const EXCHANGE_RATE_SCHEMA = z.object({
  baseCurrency: CURRENCY_CODE_SCHEMA,
  rate: z.number().positive(),
  source: z.string().optional(),
  targetCurrency: CURRENCY_CODE_SCHEMA,
  timestamp: primitiveSchemas.isoDateTime,
});

/** TypeScript type for exchange rates. */
export type ExchangeRate = z.infer<typeof EXCHANGE_RATE_SCHEMA>;

/**
 * Zod schema for currency conversion pairs.
 * Validates currency pair structure for conversion operations.
 */
export const CURRENCY_PAIR_SCHEMA = z.object({
  fromCurrency: CURRENCY_CODE_SCHEMA,
  toCurrency: CURRENCY_CODE_SCHEMA,
});

/** TypeScript type for currency pairs. */
export type CurrencyPair = z.infer<typeof CURRENCY_PAIR_SCHEMA>;

/**
 * Zod schema for currency conversion results.
 * Validates conversion result including amounts, currencies, rate, and timestamp.
 */
export const CONVERSION_RESULT_SCHEMA = z.object({
  fromAmount: z.number(),
  fromCurrency: CURRENCY_CODE_SCHEMA,
  rate: z.number().positive(),
  timestamp: primitiveSchemas.isoDateTime,
  toAmount: z.number(),
  toCurrency: CURRENCY_CODE_SCHEMA,
});

/** TypeScript type for conversion results. */
export type ConversionResult = z.infer<typeof CONVERSION_RESULT_SCHEMA>;

// ===== STATE SCHEMAS =====
// Schemas for client-side state management

/**
 * Zod schema for currency store state management.
 * Organizes currencies, exchange rates, favorites, and base currency for UI state.
 */
export const CURRENCY_STATE_SCHEMA = z.object({
  baseCurrency: CURRENCY_CODE_SCHEMA,
  currencies: z.record(CURRENCY_CODE_SCHEMA, CURRENCY_SCHEMA),
  exchangeRates: z.record(CURRENCY_CODE_SCHEMA, EXCHANGE_RATE_SCHEMA),
  favoriteCurrencies: z.array(CURRENCY_CODE_SCHEMA),
  lastUpdated: primitiveSchemas.isoDateTime.nullable(),
});

/** TypeScript type for currency store state. */
export type CurrencyState = z.infer<typeof CURRENCY_STATE_SCHEMA>;

// ===== API SCHEMAS =====
// Request/response schemas for currency API endpoints

/**
 * Zod schema for exchange rates fetch requests.
 * Validates parameters for fetching exchange rates including base currency and target currencies.
 */
export const FETCH_EXCHANGE_RATES_REQUEST_SCHEMA = z.object({
  baseCurrency: CURRENCY_CODE_SCHEMA,
  targetCurrencies: z.array(CURRENCY_CODE_SCHEMA).optional(),
});

/** TypeScript type for exchange rates fetch requests. */
export type FetchExchangeRatesRequest = z.infer<
  typeof FETCH_EXCHANGE_RATES_REQUEST_SCHEMA
>;

/**
 * Zod schema for exchange rates update responses.
 * Includes updated rates, base currency, and timestamp.
 */
export const UPDATE_EXCHANGE_RATES_RESPONSE_SCHEMA = z.object({
  baseCurrency: CURRENCY_CODE_SCHEMA,
  rates: z.record(CURRENCY_CODE_SCHEMA, z.number().positive()),
  timestamp: primitiveSchemas.isoDateTime,
});

/** TypeScript type for exchange rates update responses. */
export type UpdateExchangeRatesResponse = z.infer<
  typeof UPDATE_EXCHANGE_RATES_RESPONSE_SCHEMA
>;
