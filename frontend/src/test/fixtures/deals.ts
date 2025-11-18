/**
 * @fileoverview Zod-backed fixture builders for deals and alerts.
 * Ensures test data always matches current schema requirements.
 */

import {
  DEAL_ALERT_SCHEMA,
  DEAL_SCHEMA,
  type Deal,
  type DealAlert,
} from "@/lib/schemas/deals";
import { nowIso, secureId } from "@/lib/security/random";

/**
 * Creates a valid Deal fixture using Zod schema validation.
 *
 * @param overrides Optional partial deal to override defaults.
 * @returns A Deal object that passes DEAL_SCHEMA validation.
 */
export function createDealFixture(overrides: Partial<Deal> = {}): Deal {
  const base: Deal = {
    createdAt: nowIso(),
    currency: "USD",
    description: "Test deal description",
    destination: "Paris",
    discountPercentage: 20,
    expiryDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
    featured: false,
    id: secureId(12),
    imageUrl: "https://example.com/image.jpg",
    origin: "New York",
    originalPrice: 500,
    price: 400,
    provider: "TestProvider",
    tags: ["test"],
    title: "Test Deal",
    type: "flight",
    updatedAt: nowIso(),
    url: "https://example.com/deal",
    verified: false,
    ...overrides,
  };

  // Validate and return parsed result
  return DEAL_SCHEMA.parse(base);
}

/**
 * Creates a valid DealAlert fixture using Zod schema validation.
 *
 * @param overrides Optional partial alert to override defaults.
 * @returns A DealAlert object that passes DEAL_ALERT_SCHEMA validation.
 */
export function createDealAlertFixture(overrides: Partial<DealAlert> = {}): DealAlert {
  const base: DealAlert = {
    createdAt: nowIso(),
    dealType: "flight",
    destination: "Paris",
    id: secureId(12),
    isActive: true,
    maxPrice: 500,
    minDiscount: 20,
    notificationType: "email",
    origin: "New York",
    updatedAt: nowIso(),
    userId: "user-1",
    ...overrides,
  };

  // Validate and return parsed result
  return DEAL_ALERT_SCHEMA.parse(base);
}

/**
 * Creates an invalid deal object for testing validation failures.
 * Intentionally omits required fields or uses invalid values.
 *
 * @param invalidFields Fields to set to invalid values.
 * @returns An object that will fail DEAL_SCHEMA validation.
 */
export function createInvalidDealFixture(
  invalidFields: Partial<Record<keyof Deal, unknown>> = {}
): unknown {
  return {
    id: "invalid1",
    // Missing required fields: createdAt, currency, description, destination, expiryDate, price, provider, title, type, updatedAt, url
    ...invalidFields,
  };
}

/**
 * Creates an invalid alert object for testing validation failures.
 * Intentionally omits required fields or uses invalid values.
 *
 * @param invalidFields Fields to set to invalid values.
 * @returns An object that will fail DEAL_ALERT_SCHEMA validation.
 */
export function createInvalidDealAlertFixture(
  invalidFields: Partial<Record<keyof DealAlert, unknown>> = {}
): unknown {
  return {
    id: "invalid1",
    // Missing required fields: createdAt, id, updatedAt
    ...invalidFields,
  };
}
