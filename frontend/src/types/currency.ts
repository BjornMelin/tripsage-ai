/**
 * @fileoverview Types and schemas for currency management and exchange rates.
 */
import { z } from "zod";

// Zod schemas for validation
export const CURRENCY_CODE_SCHEMA = z
  .string()
  .length(3)
  .regex(/^[A-Z]{3}$/, {
    message: "Currency code must be a valid 3-letter ISO code",
  });

export const CURRENCY_SCHEMA = z.object({
  code: CURRENCY_CODE_SCHEMA,
  decimals: z.number().int().min(0).max(10),
  flag: z.string().optional(),
  name: z.string().min(1),
  symbol: z.string().min(1),
});

export const EXCHANGE_RATE_SCHEMA = z.object({
  baseCurrency: CURRENCY_CODE_SCHEMA,
  rate: z.number().positive(),
  source: z.string().optional(),
  targetCurrency: CURRENCY_CODE_SCHEMA,
  timestamp: z.string().datetime(),
});

export const CURRENCY_PAIR_SCHEMA = z.object({
  fromCurrency: CURRENCY_CODE_SCHEMA,
  toCurrency: CURRENCY_CODE_SCHEMA,
});

export const CONVERSION_RESULT_SCHEMA = z.object({
  fromAmount: z.number(),
  fromCurrency: CURRENCY_CODE_SCHEMA,
  rate: z.number().positive(),
  timestamp: z.string().datetime(),
  toAmount: z.number(),
  toCurrency: CURRENCY_CODE_SCHEMA,
});

export const CURRENCY_STATE_SCHEMA = z.object({
  baseCurrency: CURRENCY_CODE_SCHEMA,
  currencies: z.record(CURRENCY_CODE_SCHEMA, CURRENCY_SCHEMA),
  exchangeRates: z.record(CURRENCY_CODE_SCHEMA, EXCHANGE_RATE_SCHEMA),
  favoriteCurrencies: z.array(CURRENCY_CODE_SCHEMA),
  lastUpdated: z.string().datetime().nullable(),
});

// API Request/Response schemas
export const FETCH_EXCHANGE_RATES_REQUEST_SCHEMA = z.object({
  baseCurrency: CURRENCY_CODE_SCHEMA,
  targetCurrencies: z.array(CURRENCY_CODE_SCHEMA).optional(),
});

export const UPDATE_EXCHANGE_RATES_RESPONSE_SCHEMA = z.object({
  baseCurrency: CURRENCY_CODE_SCHEMA,
  rates: z.record(CURRENCY_CODE_SCHEMA, z.number().positive()),
  timestamp: z.string().datetime(),
});

// Inferred types from schemas
export type CurrencyCode = z.infer<typeof CURRENCY_CODE_SCHEMA>;
export type Currency = z.infer<typeof CURRENCY_SCHEMA>;
export type ExchangeRate = z.infer<typeof EXCHANGE_RATE_SCHEMA>;
export type CurrencyPair = z.infer<typeof CURRENCY_PAIR_SCHEMA>;
export type ConversionResult = z.infer<typeof CONVERSION_RESULT_SCHEMA>;
export type CurrencyState = z.infer<typeof CURRENCY_STATE_SCHEMA>;
export type FetchExchangeRatesRequest = z.infer<
  typeof FETCH_EXCHANGE_RATES_REQUEST_SCHEMA
>;
export type UpdateExchangeRatesResponse = z.infer<
  typeof UPDATE_EXCHANGE_RATES_RESPONSE_SCHEMA
>;
