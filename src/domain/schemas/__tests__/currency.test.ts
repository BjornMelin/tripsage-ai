/** @vitest-environment node */

import * as currencySchemas from "@schemas/currency";
import { CURRENCY_CODE_SCHEMA } from "@schemas/shared/money";
import { describe, expect, it } from "vitest";

describe("currency schemas", () => {
  it("keeps currency code validation owned by the shared money module", () => {
    expect(CURRENCY_CODE_SCHEMA.safeParse("USD").success).toBe(true);
    expect(CURRENCY_CODE_SCHEMA.safeParse("usd").success).toBe(false);
    expect(Object.hasOwn(currencySchemas, "CURRENCY_CODE_SCHEMA")).toBe(false);
  });

  it("validates currency metadata with the shared code schema", () => {
    const parsed = currencySchemas.CURRENCY_SCHEMA.safeParse({
      code: "EUR",
      decimals: 2,
      flag: "EU",
      name: "Euro",
      symbol: "EUR",
    });

    expect(parsed.success).toBe(true);
  });

  it("rejects invalid currency codes in currency metadata", () => {
    const parsed = currencySchemas.CURRENCY_SCHEMA.safeParse({
      code: "eur",
      decimals: 2,
      name: "Euro",
      symbol: "EUR",
    });

    expect(parsed.success).toBe(false);
  });
});
