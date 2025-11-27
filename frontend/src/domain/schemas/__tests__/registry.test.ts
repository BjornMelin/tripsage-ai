/** @vitest-environment node */

import {
  type Email,
  type IsoDateTime,
  primitiveSchemas,
  type RouteError,
  refinedSchemas,
  routeErrorSchema,
  type Timestamp,
  transformSchemas,
  type Url,
  type Uuid,
} from "@schemas/registry";
import { describe, expect, it } from "vitest";

describe("primitiveSchemas", () => {
  describe("uuid", () => {
    it.concurrent("should validate valid UUID", () => {
      const validUuid = "123e4567-e89b-12d3-a456-426614174000";
      const result = primitiveSchemas.uuid.safeParse(validUuid);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toBe(validUuid);
      }
    });

    it.concurrent("should reject invalid UUID", () => {
      const invalidUuid = "not-a-uuid";
      const result = primitiveSchemas.uuid.safeParse(invalidUuid);
      expect(result.success).toBe(false);
    });
  });

  describe("email", () => {
    it.concurrent("should validate valid email", () => {
      const validEmail = "test@example.com";
      const result = primitiveSchemas.email.safeParse(validEmail);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toBe(validEmail);
      }
    });

    it.concurrent("should reject invalid email", () => {
      const invalidEmail = "not-an-email";
      const result = primitiveSchemas.email.safeParse(invalidEmail);
      expect(result.success).toBe(false);
    });
  });

  describe("url", () => {
    it.concurrent("should validate valid URL", () => {
      const validUrl = "https://example.com";
      const result = primitiveSchemas.url.safeParse(validUrl);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toBe(validUrl);
      }
    });

    it.concurrent("should reject invalid URL", () => {
      const invalidUrl = "not-a-url";
      const result = primitiveSchemas.url.safeParse(invalidUrl);
      expect(result.success).toBe(false);
    });
  });

  describe("isoDateTime", () => {
    it.concurrent("should validate valid ISO datetime", () => {
      const validDateTime = "2024-01-01T12:00:00Z";
      const result = primitiveSchemas.isoDateTime.safeParse(validDateTime);
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject invalid ISO datetime", () => {
      const invalidDateTime = "not-a-datetime";
      const result = primitiveSchemas.isoDateTime.safeParse(invalidDateTime);
      expect(result.success).toBe(false);
    });
  });

  describe("timestamp", () => {
    it.concurrent("should validate valid timestamp", () => {
      const validTimestamp = 1704110400;
      const result = primitiveSchemas.timestamp.safeParse(validTimestamp);
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject invalid timestamp", () => {
      const invalidTimestamp = -1;
      const result = primitiveSchemas.timestamp.safeParse(invalidTimestamp);
      expect(result.success).toBe(false);
    });
  });

  describe("nonEmptyString", () => {
    it.concurrent("should validate non-empty string", () => {
      const validString = "hello";
      const result = primitiveSchemas.nonEmptyString.safeParse(validString);
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject empty string", () => {
      const emptyString = "";
      const result = primitiveSchemas.nonEmptyString.safeParse(emptyString);
      expect(result.success).toBe(false);
    });
  });

  describe("slug", () => {
    it.concurrent("should validate valid slug", () => {
      const validSlug = "hello-world-123";
      const result = primitiveSchemas.slug.safeParse(validSlug);
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject invalid slug", () => {
      const invalidSlug = "Hello World!";
      const result = primitiveSchemas.slug.safeParse(invalidSlug);
      expect(result.success).toBe(false);
    });
  });

  describe("iataCode", () => {
    it.concurrent("should validate valid IATA code", () => {
      const validCode = "JFK";
      const result = primitiveSchemas.iataCode.safeParse(validCode);
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject invalid IATA code", () => {
      const invalidCode = "jfk";
      const result = primitiveSchemas.iataCode.safeParse(invalidCode);
      expect(result.success).toBe(false);
    });
  });

  describe("isoCurrency", () => {
    it.concurrent("should validate valid currency code", () => {
      const validCurrency = "USD";
      const result = primitiveSchemas.isoCurrency.safeParse(validCurrency);
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject invalid currency code", () => {
      const invalidCurrency = "usd";
      const result = primitiveSchemas.isoCurrency.safeParse(invalidCurrency);
      expect(result.success).toBe(false);
    });
  });

  describe("positiveNumber", () => {
    it.concurrent("should validate positive number", () => {
      const validNumber = 42;
      const result = primitiveSchemas.positiveNumber.safeParse(validNumber);
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject non-positive number", () => {
      const invalidNumber = -1;
      const result = primitiveSchemas.positiveNumber.safeParse(invalidNumber);
      expect(result.success).toBe(false);
    });
  });

  describe("percentage", () => {
    it.concurrent("should validate valid percentage", () => {
      const validPercentage = 50;
      const result = primitiveSchemas.percentage.safeParse(validPercentage);
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject invalid percentage", () => {
      const invalidPercentage = 150;
      const result = primitiveSchemas.percentage.safeParse(invalidPercentage);
      expect(result.success).toBe(false);
    });
  });

  describe("nonNegativeNumber", () => {
    it.concurrent("should validate non-negative number", () => {
      const validNumber = 0;
      const result = primitiveSchemas.nonNegativeNumber.safeParse(validNumber);
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject negative number", () => {
      const invalidNumber = -1;
      const result = primitiveSchemas.nonNegativeNumber.safeParse(invalidNumber);
      expect(result.success).toBe(false);
    });
  });
});

describe("transformSchemas", () => {
  describe("trimmedString", () => {
    it.concurrent("should trim whitespace", () => {
      const input = "  hello world  ";
      const result = transformSchemas.trimmedString.safeParse(input);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toBe("hello world");
      }
    });
  });

  describe("lowercaseEmail", () => {
    it.concurrent("should convert email to lowercase", () => {
      const input = "Test@Example.COM";
      const result = transformSchemas.lowercaseEmail.safeParse(input);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toBe("test@example.com");
      }
    });
  });

  describe("normalizedUrl", () => {
    it.concurrent("should normalize URL", () => {
      const input = "  HTTPS://EXAMPLE.COM  ";
      const result = transformSchemas.normalizedUrl.safeParse(input);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toBe("https://example.com");
      }
    });
  });
});

describe("refinedSchemas", () => {
  describe("futureDate", () => {
    it.concurrent("should validate future date", () => {
      const futureDate = new Date(Date.now() + 86400000).toISOString(); // Tomorrow
      const result = refinedSchemas.futureDate.safeParse(futureDate);
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject past date", () => {
      const pastDate = new Date(Date.now() - 86400000).toISOString(); // Yesterday
      const result = refinedSchemas.futureDate.safeParse(pastDate);
      expect(result.success).toBe(false);
    });
  });

  describe("adultAge", () => {
    it.concurrent("should validate adult age", () => {
      const adultAge = 25;
      const result = refinedSchemas.adultAge.safeParse(adultAge);
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject minor age", () => {
      const minorAge = 17;
      const result = refinedSchemas.adultAge.safeParse(minorAge);
      expect(result.success).toBe(false);
    });
  });

  describe("strongPassword", () => {
    it.concurrent("should validate strong password", () => {
      const strongPassword = "Test123!Password";
      const result = refinedSchemas.strongPassword.safeParse(strongPassword);
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject weak password (no uppercase)", () => {
      const weakPassword = "test123!password";
      const result = refinedSchemas.strongPassword.safeParse(weakPassword);
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject weak password (no lowercase)", () => {
      const weakPassword = "TEST123!PASSWORD";
      const result = refinedSchemas.strongPassword.safeParse(weakPassword);
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject weak password (no numbers)", () => {
      const weakPassword = "Test!Password";
      const result = refinedSchemas.strongPassword.safeParse(weakPassword);
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject short password", () => {
      const shortPassword = "Test1!";
      const result = refinedSchemas.strongPassword.safeParse(shortPassword);
      expect(result.success).toBe(false);
    });
  });
});

describe("Type exports", () => {
  it.concurrent("should export Uuid type", () => {
    const uuid: Uuid = "123e4567-e89b-12d3-a456-426614174000";
    expect(typeof uuid).toBe("string");
  });

  it.concurrent("should export Email type", () => {
    const email: Email = "test@example.com";
    expect(typeof email).toBe("string");
  });

  it.concurrent("should export Url type", () => {
    const url: Url = "https://example.com";
    expect(typeof url).toBe("string");
  });

  it.concurrent("should export IsoDateTime type", () => {
    const dateTime: IsoDateTime = "2024-01-01T12:00:00Z";
    expect(typeof dateTime).toBe("string");
  });

  it.concurrent("should export Timestamp type", () => {
    const timestamp: Timestamp = 1704110400;
    expect(typeof timestamp).toBe("number");
  });
});

describe("Error messages", () => {
  it.concurrent("should use unified error option format", () => {
    const invalidUuid = "not-a-uuid";
    const result = primitiveSchemas.uuid.safeParse(invalidUuid);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]).toHaveProperty("message");
    }
  });
});

describe("routeErrorSchema", () => {
  it.concurrent("should validate valid route error with required fields", () => {
    const validError = {
      error: "not_found",
      reason: "Trip not found",
    };
    const result = routeErrorSchema.safeParse(validError);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.error).toBe("not_found");
      expect(result.data.reason).toBe("Trip not found");
      expect(result.data.issues).toBeUndefined();
    }
  });

  it.concurrent("should validate route error with optional issues array", () => {
    const errorWithIssues = {
      error: "invalid_request",
      issues: [
        { code: "invalid_type", message: "Expected string" },
        { message: "Required", path: ["name"] },
      ],
      reason: "Request validation failed",
    };
    const result = routeErrorSchema.safeParse(errorWithIssues);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.issues).toHaveLength(2);
    }
  });

  it.concurrent("should reject error without required error field", () => {
    const invalidError = {
      reason: "Some reason",
    };
    const result = routeErrorSchema.safeParse(invalidError);
    expect(result.success).toBe(false);
  });

  it.concurrent("should reject error without required reason field", () => {
    const invalidError = {
      error: "some_error",
    };
    const result = routeErrorSchema.safeParse(invalidError);
    expect(result.success).toBe(false);
  });

  it.concurrent("rejects empty error or reason strings", () => {
    const result = routeErrorSchema.safeParse({ error: "", reason: "" });
    expect(result.success).toBe(false);
  });

  it.concurrent("rejects non-array issues payloads", () => {
    const result = routeErrorSchema.safeParse({
      error: "bad_issues",
      issues: "not-an-array",
      reason: "Invalid issues shape",
    });
    expect(result.success).toBe(false);
  });

  it.concurrent("should allow empty issues array", () => {
    const errorWithEmptyIssues = {
      error: "validation_error",
      issues: [],
      reason: "No issues found",
    };
    const result = routeErrorSchema.safeParse(errorWithEmptyIssues);
    expect(result.success).toBe(true);
  });

  it.concurrent("should export RouteError type", () => {
    const error: RouteError = {
      error: "unauthorized",
      reason: "Authentication required",
    };
    expect(typeof error.error).toBe("string");
    expect(typeof error.reason).toBe("string");
  });
});
