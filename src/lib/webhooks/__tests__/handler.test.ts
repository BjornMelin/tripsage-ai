/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createWebhookHandler } from "../handler";

const parseAndVerifyMock = vi.hoisted(() =>
  vi.fn(async () => ({
    ok: true,
    payload: {
      occurredAt: "2025-12-10T12:00:00.000Z",
      oldRecord: null,
      record: { id: "rec-1" },
      schema: "public",
      table: "test_table",
      type: "INSERT",
    },
  }))
);

const buildEventKeyMock = vi.hoisted(() => vi.fn(() => "event-key"));
const tryReserveKeyMock = vi.hoisted(() => vi.fn(async () => true));
const checkRateLimitMock = vi.hoisted(() => vi.fn(async () => ({ success: true })));
const spanAttributes = vi.hoisted(() => [] as Array<[string, unknown]>);

vi.mock("../payload", () => ({
  buildEventKey: buildEventKeyMock,
  parseAndVerify: parseAndVerifyMock,
}));

vi.mock("@/lib/idempotency/redis", () => ({
  tryReserveKey: tryReserveKeyMock,
}));

vi.mock("../rate-limit", () => ({
  checkWebhookRateLimit: checkRateLimitMock,
  createRateLimitHeaders: () => ({}),
}));

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: async (
    _name: string,
    _opts: unknown,
    fn: (span: {
      setAttribute: (k: string, v: unknown) => void;
      recordException: () => void;
    }) => unknown
  ) =>
    fn({
      recordException: vi.fn(),
      setAttribute: (k: string, v: unknown) => {
        spanAttributes.push([k, v]);
      },
    }),
}));

describe("createWebhookHandler", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    spanAttributes.length = 0;
  });

  it("returns generic message for validation errors", async () => {
    const handler = createWebhookHandler({
      handle() {
        const validationError = new Error("invalid input");
        (validationError as Error & { code: string }).code = "VALIDATION_ERROR";
        throw validationError;
      },
      name: "test",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));
    const body = (await res.json()) as Record<string, unknown>;

    expect(res.status).toBe(400);
    expect(body).toEqual({ code: "VALIDATION_ERROR", error: "invalid_request" });
    expect(spanAttributes.some(([k]) => k === "webhook.error_message")).toBe(true);
  });

  it("masks unexpected errors as internal_error", async () => {
    const handler = createWebhookHandler({
      handle() {
        throw new Error("boom");
      },
      name: "test",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));
    const body = (await res.json()) as Record<string, unknown>;

    expect(res.status).toBe(500);
    expect(body).toEqual({ code: "UNKNOWN", error: "internal_error" });
    const recorded = spanAttributes.find(([k]) => k === "webhook.error_message");
    expect(recorded?.[1]).toBe("boom");
  });
});
