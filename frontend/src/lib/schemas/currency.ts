/**
 * @fileoverview Zod v4 schemas for currency management and exchange rates.
 */

import { z } from "zod";

/** Zod schema for ISO 4217 currency codes (3-letter uppercase). */
export const CURRENCY_CODE_SCHEMA = z
  .string()
  .length(3)
  .regex(/^[A-Z]{3}$/, { message: "Currency code must be a valid 3-letter ISO code" });

/** Zod schema for currency metadata and display information. */
export const CURRENCY_SCHEMA = z.object({
  code: CURRENCY_CODE_SCHEMA,
  decimals: z.number().int().min(0).max(10),
  flag: z.string().optional(),
  name: z.string().min(1),
  symbol: z.string().min(1),
});

/** Zod schema for currency exchange rate data. */
export const EXCHANGE_RATE_SCHEMA = z.object({
  baseCurrency: CURRENCY_CODE_SCHEMA,
  rate: z.number().positive(),
  source: z.string().optional(),
  targetCurrency: CURRENCY_CODE_SCHEMA,
  timestamp: z.iso.datetime(),
});

/** Zod schema for currency conversion pairs. */
export const CURRENCY_PAIR_SCHEMA = z.object({
  fromCurrency: CURRENCY_CODE_SCHEMA,
  toCurrency: CURRENCY_CODE_SCHEMA,
});

/** Zod schema for currency conversion results. */
export const CONVERSION_RESULT_SCHEMA = z.object({
  fromAmount: z.number(),
  fromCurrency: CURRENCY_CODE_SCHEMA,
  rate: z.number().positive(),
  timestamp: z.iso.datetime(),
  toAmount: z.number(),
  toCurrency: CURRENCY_CODE_SCHEMA,
});

/** Zod schema for currency store state management. */
export const CURRENCY_STATE_SCHEMA = z.object({
  baseCurrency: CURRENCY_CODE_SCHEMA,
  currencies: z.record(CURRENCY_CODE_SCHEMA, CURRENCY_SCHEMA),
  exchangeRates: z.record(CURRENCY_CODE_SCHEMA, EXCHANGE_RATE_SCHEMA),
  favoriteCurrencies: z.array(CURRENCY_CODE_SCHEMA),
  lastUpdated: z.iso.datetime().nullable(),
});

/** Zod schema for exchange rates fetch requests. */
export const FETCH_EXCHANGE_RATES_REQUEST_SCHEMA = z.object({
  baseCurrency: CURRENCY_CODE_SCHEMA,
  targetCurrencies: z.array(CURRENCY_CODE_SCHEMA).optional(),
});

/** Zod schema for exchange rates update responses. */
export const UPDATE_EXCHANGE_RATES_RESPONSE_SCHEMA = z.object({
  baseCurrency: CURRENCY_CODE_SCHEMA,
  rates: z.record(CURRENCY_CODE_SCHEMA, z.number().positive()),
  timestamp: z.iso.datetime(),
});

/** TypeScript type for currency codes. */
export type CurrencyCode = z.infer<typeof CURRENCY_CODE_SCHEMA>;
/** TypeScript type for currency metadata. */
export type Currency = z.infer<typeof CURRENCY_SCHEMA>;
/** TypeScript type for exchange rates. */
export type ExchangeRate = z.infer<typeof EXCHANGE_RATE_SCHEMA>;
/** TypeScript type for currency pairs. */
export type CurrencyPair = z.infer<typeof CURRENCY_PAIR_SCHEMA>;
/** TypeScript type for conversion results. */
export type ConversionResult = z.infer<typeof CONVERSION_RESULT_SCHEMA>;
/** TypeScript type for currency store state. */
export type CurrencyState = z.infer<typeof CURRENCY_STATE_SCHEMA>;
/** TypeScript type for exchange rates fetch requests. */
export type FetchExchangeRatesRequest = z.infer<
  typeof FETCH_EXCHANGE_RATES_REQUEST_SCHEMA
>;
/** TypeScript type for exchange rates update responses. */
export type UpdateExchangeRatesResponse = z.infer<
  typeof UPDATE_EXCHANGE_RATES_RESPONSE_SCHEMA
>;
