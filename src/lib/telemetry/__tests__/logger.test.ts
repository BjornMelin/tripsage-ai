/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

const RECORD_TELEMETRY_EVENT = vi.hoisted(() => vi.fn());

vi.mock("@/lib/telemetry/span", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/telemetry/span")>();
  return {
    ...actual,
    recordTelemetryEvent: RECORD_TELEMETRY_EVENT,
  };
});

const { createServerLogger } = await import("@/lib/telemetry/logger");

describe("createServerLogger", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("redacts metadata keys specified in redactKeys", () => {
    const logger = createServerLogger("api.keys", { redactKeys: ["apiKey"] });
    logger.info("Key stored", { apiKey: "sk-test", userId: "user-123" });

    expect(RECORD_TELEMETRY_EVENT).toHaveBeenCalledWith(
      "log.api.keys",
      expect.objectContaining({
        attributes: expect.objectContaining({
          "log.apiKey": "[REDACTED]",
        }),
        level: "info",
      })
    );
  });

  it("accepts already-prefixed redact keys", () => {
    const logger = createServerLogger("api.keys", { redactKeys: ["log.apiKey"] });
    logger.info("Key stored", { apiKey: "sk-test" });

    expect(RECORD_TELEMETRY_EVENT).toHaveBeenCalledWith(
      "log.api.keys",
      expect.objectContaining({
        attributes: expect.objectContaining({
          "log.apiKey": "[REDACTED]",
        }),
      })
    );
  });

  it("redacts sensitive keys inside nested metadata values", () => {
    const logger = createServerLogger("api.keys");
    logger.error("boom", {
      config: { apiKey: "sk-test", nested: { token: "secret-token" } },
      token: "top-level-token",
    });

    expect(RECORD_TELEMETRY_EVENT).toHaveBeenCalledTimes(1);
    const [, payload] = RECORD_TELEMETRY_EVENT.mock.calls[0] ?? [];
    expect(payload).toEqual(
      expect.objectContaining({
        attributes: expect.objectContaining({
          "log.token": "[REDACTED]",
        }),
      })
    );
    const configValue = payload?.attributes?.["log.config"] as unknown;
    expect(typeof configValue).toBe("string");
    expect(String(configValue)).toContain('"apiKey":"[REDACTED]"');
    expect(String(configValue)).toContain('"token":"[REDACTED]"');
  });

  it("redacts error fields by default", () => {
    const logger = createServerLogger("api.keys");
    logger.error("boom", {
      error: "provider said: something sensitive",
      errorMessage: "extra details",
    });

    expect(RECORD_TELEMETRY_EVENT).toHaveBeenCalledWith(
      "log.api.keys",
      expect.objectContaining({
        attributes: expect.objectContaining({
          "log.error": "[REDACTED]",
          "log.errorMessage": "[REDACTED]",
        }),
        level: "error",
      })
    );
  });

  it("can redact the primary message when configured", () => {
    const logger = createServerLogger("api.keys", { redactMessage: true });
    logger.info("user entered: 123 main street", { ok: true });

    expect(RECORD_TELEMETRY_EVENT).toHaveBeenCalledWith(
      "log.api.keys",
      expect.objectContaining({
        attributes: expect.objectContaining({
          "log.message": "[REDACTED]",
        }),
        level: "info",
      })
    );
  });
});
