/**
 * @fileoverview Types and schemas for currency management and exchange rates.
 */
import { z } from "zod";

// Zod schemas for validation
export const CurrencyCodeSchema = z
  .string()
  .length(3)
  .regex(/^[A-Z]{3}$/, {
    message: "Currency code must be a valid 3-letter ISO code",
  });

export const CurrencySchema = z.object({
  code: CurrencyCodeSchema,
  decimals: z.number().int().min(0).max(10),
  flag: z.string().optional(),
  name: z.string().min(1),
  symbol: z.string().min(1),
});

export const ExchangeRateSchema = z.object({
  baseCurrency: CurrencyCodeSchema,
  rate: z.number().positive(),
  source: z.string().optional(),
  targetCurrency: CurrencyCodeSchema,
  timestamp: z.string().datetime(),
});

export const CurrencyPairSchema = z.object({
  fromCurrency: CurrencyCodeSchema,
  toCurrency: CurrencyCodeSchema,
});

export const ConversionResultSchema = z.object({
  fromAmount: z.number(),
  fromCurrency: CurrencyCodeSchema,
  rate: z.number().positive(),
  timestamp: z.string().datetime(),
  toAmount: z.number(),
  toCurrency: CurrencyCodeSchema,
});

export const CurrencyStateSchema = z.object({
  baseCurrency: CurrencyCodeSchema,
  currencies: z.record(CurrencyCodeSchema, CurrencySchema),
  exchangeRates: z.record(CurrencyCodeSchema, ExchangeRateSchema),
  favoriteCurrencies: z.array(CurrencyCodeSchema),
  lastUpdated: z.string().datetime().nullable(),
});

// API Request/Response schemas
export const FetchExchangeRatesRequestSchema = z.object({
  baseCurrency: CurrencyCodeSchema,
  targetCurrencies: z.array(CurrencyCodeSchema).optional(),
});

export const UpdateExchangeRatesResponseSchema = z.object({
  baseCurrency: CurrencyCodeSchema,
  rates: z.record(CurrencyCodeSchema, z.number().positive()),
  timestamp: z.string().datetime(),
});

// Inferred types from schemas
export type CurrencyCode = z.infer<typeof CurrencyCodeSchema>;
export type Currency = z.infer<typeof CurrencySchema>;
export type ExchangeRate = z.infer<typeof ExchangeRateSchema>;
export type CurrencyPair = z.infer<typeof CurrencyPairSchema>;
export type ConversionResult = z.infer<typeof ConversionResultSchema>;
export type CurrencyState = z.infer<typeof CurrencyStateSchema>;
export type FetchExchangeRatesRequest = z.infer<typeof FetchExchangeRatesRequestSchema>;
export type UpdateExchangeRatesResponse = z.infer<
  typeof UpdateExchangeRatesResponseSchema
>;
