/**
 * @fileoverview Shared money/currency primitives.
 */

import { z } from "zod";
import { primitiveSchemas } from "../registry";

export const CURRENCY_CODE_SCHEMA = primitiveSchemas.isoCurrency;

export const PRICE_SCHEMA = z.strictObject({
  amount: z.number().positive(),
  currency: CURRENCY_CODE_SCHEMA,
});

export type CurrencyCode = z.infer<typeof CURRENCY_CODE_SCHEMA>;
export type Price = z.infer<typeof PRICE_SCHEMA>;
