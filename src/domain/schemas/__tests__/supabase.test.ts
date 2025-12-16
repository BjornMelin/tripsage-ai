/** @vitest-environment node */

import {
  apiMetricsInsertSchema,
  apiMetricsRowSchema,
  apiMetricsUpdateSchema,
  httpMethodSchema,
  supabaseSchemas,
} from "@schemas/supabase";
import { describe, expect, it } from "vitest";

describe("httpMethodSchema", () => {
  const validMethods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"];

  it.each(validMethods)("should accept valid HTTP method: %s", (method) => {
    const result = httpMethodSchema.safeParse(method);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data).toBe(method);
    }
  });

  it.concurrent("should reject invalid HTTP method", () => {
    const result = httpMethodSchema.safeParse("INVALID");
    expect(result.success).toBe(false);
  });

  it.concurrent("should reject lowercase methods", () => {
    const result = httpMethodSchema.safeParse("get");
    expect(result.success).toBe(false);
  });
});

describe("apiMetricsRowSchema", () => {
  const validRow = {
    created_at: "2024-01-15T10:30:00.000Z",
    duration_ms: 150.5,
    endpoint: "/api/dashboard",
    error_type: null,
    id: "123e4567-e89b-12d3-a456-426614174000",
    method: "GET",
    rate_limit_key: null,
    status_code: 200,
    user_id: "123e4567-e89b-12d3-a456-426614174001",
  };

  it.concurrent("should validate a complete row", () => {
    const result = apiMetricsRowSchema.safeParse(validRow);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.endpoint).toBe("/api/dashboard");
      expect(result.data.method).toBe("GET");
      expect(result.data.status_code).toBe(200);
    }
  });

  it.concurrent("should accept nullable user_id", () => {
    const result = apiMetricsRowSchema.safeParse({
      ...validRow,
      user_id: null,
    });
    expect(result.success).toBe(true);
  });

  it.concurrent("should accept error_type and rate_limit_key", () => {
    const result = apiMetricsRowSchema.safeParse({
      ...validRow,
      error_type: "ValidationError",
      rate_limit_key: "user:123",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.error_type).toBe("ValidationError");
      expect(result.data.rate_limit_key).toBe("user:123");
    }
  });

  it.concurrent("should reject invalid status codes", () => {
    const tooLow = apiMetricsRowSchema.safeParse({
      ...validRow,
      status_code: 50,
    });
    expect(tooLow.success).toBe(false);

    const tooHigh = apiMetricsRowSchema.safeParse({
      ...validRow,
      status_code: 600,
    });
    expect(tooHigh.success).toBe(false);
  });

  it.concurrent("should accept boundary status codes (100 and 599)", () => {
    const minValid = apiMetricsRowSchema.safeParse({
      ...validRow,
      status_code: 100,
    });
    expect(minValid.success).toBe(true);

    const maxValid = apiMetricsRowSchema.safeParse({
      ...validRow,
      status_code: 599,
    });
    expect(maxValid.success).toBe(true);
  });

  it.concurrent("should reject negative duration_ms", () => {
    const result = apiMetricsRowSchema.safeParse({
      ...validRow,
      duration_ms: -10,
    });
    expect(result.success).toBe(false);
  });

  it.concurrent("should accept zero duration_ms", () => {
    const result = apiMetricsRowSchema.safeParse({
      ...validRow,
      duration_ms: 0,
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.duration_ms).toBe(0);
    }
  });

  it.concurrent("should reject invalid UUID for id", () => {
    const result = apiMetricsRowSchema.safeParse({
      ...validRow,
      id: "not-a-uuid",
    });
    expect(result.success).toBe(false);
  });

  it.concurrent("should reject empty endpoint", () => {
    const result = apiMetricsRowSchema.safeParse({
      ...validRow,
      endpoint: "",
    });
    expect(result.success).toBe(false);
  });
});

describe("apiMetricsInsertSchema", () => {
  it.concurrent("should validate minimal insert payload", () => {
    const minimal = {
      duration_ms: 50,
      endpoint: "/api/test",
      method: "POST",
      status_code: 201,
    };
    const result = apiMetricsInsertSchema.safeParse(minimal);
    expect(result.success).toBe(true);
  });

  it.concurrent("should allow optional fields", () => {
    const withOptional = {
      duration_ms: 1000,
      endpoint: "/api/test",
      error_type: "InternalServerError",
      method: "DELETE",
      rate_limit_key: "ip:192.168.1.1",
      status_code: 500,
      user_id: "123e4567-e89b-12d3-a456-426614174000",
    };
    const result = apiMetricsInsertSchema.safeParse(withOptional);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.error_type).toBe("InternalServerError");
    }
  });

  it.concurrent("should reject missing required fields", () => {
    const missing = {
      endpoint: "/api/test",
      // missing method, status_code, duration_ms
    };
    const result = apiMetricsInsertSchema.safeParse(missing);
    expect(result.success).toBe(false);
  });

  it.concurrent("should accept valid created_at ISO datetime", () => {
    const withCreatedAt = {
      created_at: "2024-06-15T14:30:00.000Z",
      duration_ms: 100,
      endpoint: "/api/test",
      method: "GET",
      status_code: 200,
    };
    const result = apiMetricsInsertSchema.safeParse(withCreatedAt);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.created_at).toBe("2024-06-15T14:30:00.000Z");
    }
  });

  it.concurrent("should reject invalid created_at format", () => {
    const invalidDate = {
      created_at: "not-a-date",
      duration_ms: 100,
      endpoint: "/api/test",
      method: "GET",
      status_code: 200,
    };
    const result = apiMetricsInsertSchema.safeParse(invalidDate);
    expect(result.success).toBe(false);

    const wrongFormat = {
      created_at: "2024/06/15 14:30:00",
      duration_ms: 100,
      endpoint: "/api/test",
      method: "GET",
      status_code: 200,
    };
    const result2 = apiMetricsInsertSchema.safeParse(wrongFormat);
    expect(result2.success).toBe(false);
  });
});

describe("apiMetricsUpdateSchema", () => {
  it.concurrent("should allow partial updates", () => {
    const partial = {
      status_code: 404,
    };
    const result = apiMetricsUpdateSchema.safeParse(partial);
    expect(result.success).toBe(true);
  });

  it.concurrent("should allow empty object (no updates)", () => {
    const result = apiMetricsUpdateSchema.safeParse({});
    expect(result.success).toBe(true);
  });

  it.concurrent("should validate updated fields", () => {
    const invalidUpdate = {
      status_code: 9999, // out of range
    };
    const result = apiMetricsUpdateSchema.safeParse(invalidUpdate);
    expect(result.success).toBe(false);
  });
});

describe("supabaseSchemas.api_metrics", () => {
  it.concurrent("should have all schema variants", () => {
    expect(supabaseSchemas.api_metrics).toBeDefined();
    expect(supabaseSchemas.api_metrics.row).toBeDefined();
    expect(supabaseSchemas.api_metrics.insert).toBeDefined();
    expect(supabaseSchemas.api_metrics.update).toBeDefined();
  });

  it.concurrent("should parse row data correctly", () => {
    const row = {
      created_at: "2024-01-01T00:00:00.000Z",
      duration_ms: 5,
      endpoint: "/api/health",
      error_type: null,
      id: "123e4567-e89b-12d3-a456-426614174000",
      method: "GET",
      rate_limit_key: null,
      status_code: 200,
      user_id: null,
    };
    const result = supabaseSchemas.api_metrics.row.safeParse(row);
    expect(result.success).toBe(true);
  });
});
