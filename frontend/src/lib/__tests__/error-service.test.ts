/** @vitest-environment node */

import type { ErrorReport, ErrorServiceConfig } from "@schemas/errors";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as telemetryClientErrors from "@/lib/telemetry/client-errors";
import { createMockStorage } from "@/test/mocks/storage";
import {
  createErrorReportingRecorder,
  createFlakyErrorReportingHandler,
  ERROR_REPORTING_ENDPOINT,
} from "@/test/msw/handlers/error-reporting";
import { server } from "@/test/msw/server";
import { ErrorService } from "../error-service";

type StorageMocks = {
  localStorageMock: Storage;
  sessionStorageMock: Storage;
};

const setupBrowserEnv = (): StorageMocks => {
  const location = { href: "https://example.com/" } as Location;
  const navigator = { userAgent: "Vitest" } as Navigator;

  const localStorageMock = createMockStorage();
  const sessionStorageMock = createMockStorage();

  const win = {
    localStorage: localStorageMock,
    location,
    navigator,
    sessionStorage: sessionStorageMock,
  } as unknown as Window & typeof globalThis;

  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: win,
    writable: true,
  });
  Object.defineProperty(globalThis, "location", {
    configurable: true,
    value: location,
    writable: true,
  });
  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: navigator,
    writable: true,
  });
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: localStorageMock,
    writable: true,
  });
  Object.defineProperty(globalThis, "sessionStorage", {
    configurable: true,
    value: sessionStorageMock,
    writable: true,
  });

  return { localStorageMock, sessionStorageMock };
};

const teardownBrowserEnv = () => {
  (globalThis as { window?: Window }).window = undefined;
  (globalThis as { location?: Location }).location = undefined;
  (globalThis as { navigator?: Navigator }).navigator = undefined;
  (globalThis as { localStorage?: Storage }).localStorage = undefined;
  (globalThis as { sessionStorage?: Storage }).sessionStorage = undefined;
};

const buildReport = (): ErrorReport => ({
  error: {
    message: "Test error",
    name: "Error",
  },
  timestamp: new Date().toISOString(),
  url: "https://example.com/",
  userAgent: "Vitest",
});

describe("ErrorService", () => {
  let errorService: ErrorService;
  let config: ErrorServiceConfig;
  let localStorageMock: Storage;
  let _sessionStorageMock: Storage;

  beforeEach(() => {
    ({ localStorageMock, sessionStorageMock: _sessionStorageMock } = setupBrowserEnv());

    config = {
      apiKey: "test-api-key",
      enabled: true,
      enableLocalStorage: true,
      endpoint: ERROR_REPORTING_ENDPOINT,
      maxRetries: 2,
    };

    errorService = new ErrorService(config);
  });

  afterEach(() => {
    teardownBrowserEnv();
    vi.clearAllTimers();
  });

  describe("createErrorReport", () => {
    it("builds a report with runtime context and optional details", () => {
      const error = new Error("Test error");
      error.stack = "Error: Test error\n    at test (test.js:1:1)";

      const report = errorService.createErrorReport(
        error,
        { componentStack: "Component.tsx:10:5" },
        { sessionId: "session-1", userId: "user-1" }
      );

      expect(report.error).toMatchObject({
        message: "Test error",
        name: "Error",
        stack: "Error: Test error\n    at test (test.js:1:1)",
      });
      expect(report.errorInfo).toEqual({ componentStack: "Component.tsx:10:5" });
      expect(report.sessionId).toBe("session-1");
      expect(report.userId).toBe("user-1");
      expect(report.url).toBe("https://example.com/");
      expect(report.userAgent).toBe("Vitest");
      expect(new Date(report.timestamp).toISOString()).toBe(report.timestamp);
    });

    it("includes error digests when present", () => {
      const error = new Error("Test error") as Error & { digest?: string };
      error.digest = "abc123";

      const report = errorService.createErrorReport(error);

      expect(report.error.digest).toBe("abc123");
    });
  });

  describe("reportError", () => {
    it("sends validated reports to the configured endpoint", async () => {
      const recorder = createErrorReportingRecorder(config.endpoint);
      server.use(recorder.handler);

      const errorReport = buildReport();

      await errorService.reportError(errorReport);

      expect(recorder.requests).toHaveLength(1);
      const [request] = recorder.requests;
      expect(request.body).toEqual(errorReport);
      expect(request.headers.get("Authorization")).toBe("Bearer test-api-key");
      expect(request.headers.get("Content-Type")).toBe("application/json");
    });

    it("logs locally and skips network calls when disabled", async () => {
      const recorder = createErrorReportingRecorder(config.endpoint);
      server.use(recorder.handler);
      const disabledService = new ErrorService({ ...config, enabled: false });
      const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {
        // Suppress console.error output in tests
      });
      const errorReport = buildReport();

      await disabledService.reportError(errorReport);

      expect(recorder.requests).toHaveLength(0);
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Error reported:",
        expect.objectContaining(errorReport)
      );
    });

    it("persists errors to localStorage when enabled", async () => {
      const recorder = createErrorReportingRecorder(config.endpoint);
      server.use(recorder.handler);
      const errorReport = buildReport();

      await errorService.reportError(errorReport);

      const setItemMock = localStorageMock.setItem as ReturnType<typeof vi.fn>;
      expect(setItemMock).toHaveBeenCalledTimes(1);
      const [key, value] = setItemMock.mock.calls[0] as [string, string];
      expect(key).toMatch(/^error_\d+_[a-z0-9]+$/);
      expect(JSON.parse(value)).toEqual(errorReport);
    });

    it("rejects invalid reports via Zod validation", async () => {
      const recorder = createErrorReportingRecorder(config.endpoint);
      server.use(recorder.handler);
      const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {
        // Suppress console.error output in tests
      });

      const invalidReport = {
        error: { name: "Error" },
        timestamp: new Date().toISOString(),
        url: "https://example.com",
        userAgent: "Vitest",
      } as unknown as ErrorReport;

      await errorService.reportError(invalidReport);

      expect(recorder.requests).toHaveLength(0);
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to report error:",
        expect.any(Error)
      );
    });
  });

  describe("error reporting with retries", () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("retries transient failures up to maxRetries", async () => {
      const flaky = createFlakyErrorReportingHandler({
        endpoint: config.endpoint,
        failTimes: 1,
      });
      server.use(flaky.handler);

      await errorService.reportError(buildReport());

      await vi.advanceTimersByTimeAsync(1000);

      expect(flaky.callCount()).toBe(2);
    });

    it("stops retrying after exceeding maxRetries", async () => {
      const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {
        // Suppress console.error output in tests
      });
      const flaky = createFlakyErrorReportingHandler({
        endpoint: config.endpoint,
        failTimes: 5,
      });
      server.use(flaky.handler);

      await errorService.reportError(buildReport());

      await vi.advanceTimersByTimeAsync(4000);

      expect(flaky.callCount()).toBe(3);
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to send error report after retries:",
        expect.any(Error)
      );
    });
  });

  describe("localStorage cleanup", () => {
    it("keeps only the newest 10 error records", async () => {
      const recorder = createErrorReportingRecorder(config.endpoint);
      server.use(recorder.handler);

      const existingKeys = Array.from(
        { length: 12 },
        (_, index) => `error_${index.toString().padStart(4, "0")}`
      );
      existingKeys.forEach((key) => {
        localStorageMock.setItem(key, JSON.stringify({ key }));
      });

      const originalObjectKeys = Object.keys;
      const objectKeysSpy = vi
        .spyOn(Object, "keys")
        .mockImplementation((target: object) => {
          if (target === localStorageMock) {
            const keys: string[] = [];
            for (let i = 0; i < localStorageMock.length; i++) {
              const keyName = localStorageMock.key(i);
              if (keyName) keys.push(keyName);
            }
            return keys;
          }
          return originalObjectKeys(target);
        });

      await errorService.reportError(buildReport());

      const removeItemMock = localStorageMock.removeItem as ReturnType<typeof vi.fn>;
      // 12 existing + 1 new => 13 total; keep 10 => remove 3 oldest
      expect(removeItemMock).toHaveBeenCalledTimes(3);

      objectKeysSpy.mockRestore();
    });
  });

  describe("OpenTelemetry integration", () => {
    let recordClientErrorOnActiveSpanSpy: ReturnType<typeof vi.spyOn>;

    beforeEach(() => {
      recordClientErrorOnActiveSpanSpy = vi.spyOn(
        telemetryClientErrors,
        "recordClientErrorOnActiveSpan"
      );
    });

    afterEach(() => {
      recordClientErrorOnActiveSpanSpy.mockRestore();
    });

    it("records errors on the active span when details are present", async () => {
      const recorder = createErrorReportingRecorder(config.endpoint);
      server.use(recorder.handler);

      await errorService.reportError({
        ...buildReport(),
        error: {
          message: "Test error",
          name: "TestError",
          stack: "Error: Test error\n    at test (test.js:1:1)",
        },
      });

      expect(recordClientErrorOnActiveSpanSpy).toHaveBeenCalledTimes(1);
      const [capturedError] = recordClientErrorOnActiveSpanSpy.mock.calls[0];
      expect(capturedError).toBeInstanceOf(Error);
      expect(capturedError.message).toBe("Test error");
      expect(capturedError.name).toBe("TestError");
    });

    it("logs a warning when OpenTelemetry recording fails but still reports", async () => {
      const consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {
        // Suppress console.warn output in tests
      });
      recordClientErrorOnActiveSpanSpy.mockImplementation(() => {
        throw new Error("OTel recording failed");
      });
      const recorder = createErrorReportingRecorder(config.endpoint);
      server.use(recorder.handler);

      await expect(errorService.reportError(buildReport())).resolves.not.toThrow();

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        "Failed to record error to OpenTelemetry span:",
        expect.any(Error)
      );
    });
  });
});
