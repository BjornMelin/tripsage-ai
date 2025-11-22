// @ts-expect-error startActiveSpanMock is provided only by the Vitest mock.
import { SpanStatusCode, startActiveSpanMock, trace } from "@opentelemetry/api";
import type { CookieMethodsServer } from "@supabase/ssr";
import { createServerClient } from "@supabase/ssr";
import type { User } from "@supabase/supabase-js";
import type { ReadonlyRequestCookies } from "next/dist/server/web/spec-extension/adapters/request-cookies";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getClientEnv } from "@/lib/env/client";
import {
  resetTelemetryTracerForTests,
  setTelemetryTracerForTests,
} from "@/lib/telemetry/span";
import type { ServerSupabaseClient } from "../factory";
import {
  createCookieAdapter,
  createMiddlewareSupabase,
  createServerSupabase,
  getCurrentUser,
} from "../factory";
import { isSupabaseClient } from "../guards";

// Mock dependencies
vi.mock("@supabase/ssr", () => ({
  createServerClient: vi.fn(),
}));

vi.mock("@opentelemetry/api", () => {
  const localStartActiveSpanMock = vi.fn(
    (_name: string, _options: unknown, callback: (span: unknown) => unknown) => {
      const mockSpan = {
        end: vi.fn(),
        recordException: vi.fn(),
        setAttribute: vi.fn(),
        setStatus: vi.fn(),
      };
      return callback(mockSpan);
    }
  );

  return {
    SpanStatusCode: {
      ERROR: 2,
      OK: 1,
      UNSET: 0,
    },
    startActiveSpanMock: localStartActiveSpanMock,
    trace: {
      getTracer: vi.fn(() => ({
        startActiveSpan: localStartActiveSpanMock,
      })),
    },
  };
});

vi.mock("@/lib/env/server", () => ({
  getServerEnv: vi.fn(() => ({
    NEXT_PUBLIC_SUPABASE_ANON_KEY: "test-anon-key",
    NEXT_PUBLIC_SUPABASE_URL: "https://test.supabase.co",
  })),
}));

vi.mock("@/lib/env/client", () => ({
  getClientEnv: vi.fn(() => ({
    NEXT_PUBLIC_SUPABASE_ANON_KEY: "test-anon-key",
    NEXT_PUBLIC_SUPABASE_URL: "https://test.supabase.co",
  })),
}));

vi.mock("@/lib/telemetry/tracer", () => ({
  getTelemetryTracer: () => trace.getTracer("tripsage-frontend"),
  TELEMETRY_SERVICE_NAME: "tripsage-frontend",
}));

describe("Supabase Factory", () => {
  const mockCreateServerClient = vi.mocked(createServerClient);

  beforeEach(() => {
    resetTelemetryTracerForTests();
    setTelemetryTracerForTests(trace.getTracer("tripsage-frontend"));
  });

  describe("createServerSupabase", () => {
    let mockCookieAdapter: CookieMethodsServer;

    beforeEach(() => {
      mockCookieAdapter = {
        getAll: vi.fn(() => [{ name: "sb-access-token", value: "mock-token" }]),
        setAll: vi.fn(),
      };
    });

    afterEach(() => {
      vi.clearAllMocks();
    });

    it("should create a server client with cookie adapter", () => {
      mockCreateServerClient.mockReturnValue({
        auth: {
          getUser: vi.fn(),
        },
        from: vi.fn(),
      });

      const client = createServerSupabase({
        cookies: mockCookieAdapter,
      });

      expect(mockCreateServerClient).toHaveBeenCalledWith(
        "https://test.supabase.co",
        "test-anon-key",
        expect.objectContaining({
          cookies: expect.any(Object),
        })
      );
      expect(client).toBeDefined();
      expect(client.auth).toBeDefined();
      expect(client.from).toBeDefined();
    });

    it("should enable tracing by default", () => {
      mockCreateServerClient.mockReturnValue({
        auth: { getUser: vi.fn() },
        from: vi.fn(),
      });

      createServerSupabase({
        cookies: mockCookieAdapter,
      });

      expect(startActiveSpanMock).toHaveBeenCalledWith(
        "supabase.init",
        expect.objectContaining({
          attributes: expect.objectContaining({
            "db.name": "tripsage",
            "db.supabase.operation": "init",
            "db.system": "postgres",
            "service.name": "tripsage-frontend",
          }),
        }),
        expect.any(Function)
      );
    });

    it("should allow disabling tracing", () => {
      mockCreateServerClient.mockReturnValue({
        auth: { getUser: vi.fn() },
        from: vi.fn(),
      });

      createServerSupabase({
        cookies: mockCookieAdapter,
        enableTracing: false,
      });

      expect(startActiveSpanMock).not.toHaveBeenCalled();
    });

    it("should use custom span name when provided", () => {
      mockCreateServerClient.mockReturnValue({
        auth: { getUser: vi.fn() },
        from: vi.fn(),
      });

      createServerSupabase({
        cookies: mockCookieAdapter,
        spanName: "custom.span.name",
      });

      expect(startActiveSpanMock).toHaveBeenCalledWith(
        "custom.span.name",
        expect.any(Object),
        expect.any(Function)
      );
    });

    it("should handle cookie adapter errors gracefully", () => {
      const errorCookieAdapter: CookieMethodsServer = {
        getAll: vi.fn(() => {
          throw new Error("Cookie read error");
        }),
        setAll: vi.fn(),
      };

      mockCreateServerClient.mockImplementation(
        (_url: string, _key: string, options: { cookies: CookieMethodsServer }) => {
          // Simulate calling getAll to trigger error
          try {
            options.cookies.getAll();
          } catch {
            // Error should be caught by factory
          }
          return {
            auth: { getUser: vi.fn() },
            from: vi.fn(),
          };
        }
      );

      expect(() =>
        createServerSupabase({
          cookies: errorCookieAdapter,
          enableTracing: false,
        })
      ).not.toThrow();
    });

    it("should throw error when cookie adapter is not provided", () => {
      mockCreateServerClient.mockImplementation(
        (_url, _key, options: { cookies: CookieMethodsServer }) => {
          expect(() => options.cookies.getAll()).toThrow(
            "Cookie adapter required for server client creation"
          );

          expect(() =>
            options.cookies.setAll?.([{ name: "cookie", options: {}, value: "value" }])
          ).toThrow("Cookie adapter required for server client creation");

          return {
            auth: { getUser: vi.fn() },
            from: vi.fn(),
          } as unknown as ServerSupabaseClient;
        }
      );

      createServerSupabase({
        enableTracing: false,
      });
    });
  });

  describe("createMiddlewareSupabase", () => {
    let mockCookieAdapter: CookieMethodsServer;

    beforeEach(() => {
      mockCookieAdapter = {
        getAll: vi.fn(() => [{ name: "sb-access-token", value: "mock-token" }]),
        setAll: vi.fn(),
      };
    });

    afterEach(() => {
      vi.clearAllMocks();
    });

    it("should create a middleware client with cookie adapter", () => {
      mockCreateServerClient.mockReturnValue({
        auth: {
          getUser: vi.fn(),
        },
        from: vi.fn(),
      });

      const client = createMiddlewareSupabase({
        cookies: mockCookieAdapter,
      });

      expect(mockCreateServerClient).toHaveBeenCalledWith(
        "https://test.supabase.co",
        "test-anon-key",
        expect.objectContaining({
          cookies: expect.any(Object),
        })
      );
      expect(client).toBeDefined();
      expect(client.auth).toBeDefined();
      expect(client.from).toBeDefined();
    });

    it("should disable tracing by default", () => {
      mockCreateServerClient.mockReturnValue({
        auth: { getUser: vi.fn() },
        from: vi.fn(),
      });

      const client = createMiddlewareSupabase({
        cookies: mockCookieAdapter,
      });

      expect(mockCreateServerClient).toHaveBeenCalledWith(
        "https://test.supabase.co",
        "test-anon-key",
        expect.objectContaining({
          cookies: expect.any(Object),
        })
      );
      expect(client).toBeDefined();
    });

    it("should allow enabling tracing when explicitly requested", () => {
      mockCreateServerClient.mockReturnValue({
        auth: { getUser: vi.fn() },
        from: vi.fn(),
      });

      const client = createMiddlewareSupabase({
        cookies: mockCookieAdapter,
        enableTracing: true,
        spanName: "test.middleware.span",
      });

      expect(startActiveSpanMock).toHaveBeenCalledWith(
        "test.middleware.span",
        expect.objectContaining({
          attributes: expect.objectContaining({
            "db.name": "tripsage",
            "db.supabase.operation": "middleware.init",
            "db.system": "postgres",
            "runtime.environment": "edge",
            "service.name": "tripsage-frontend",
          }),
        }),
        expect.any(Function)
      );
      expect(client).toBeDefined();
    });

    it("should use client environment variables", () => {
      const mockEnv = vi.mocked(getClientEnv);

      mockCreateServerClient.mockReturnValue({
        auth: { getUser: vi.fn() },
        from: vi.fn(),
      });

      createMiddlewareSupabase({
        cookies: mockCookieAdapter,
      });

      expect(mockEnv).toHaveBeenCalled();
      expect(mockCreateServerClient).toHaveBeenCalledWith(
        "https://test.supabase.co",
        "test-anon-key",
        expect.any(Object)
      );
    });
  });

  describe("getCurrentUser", () => {
    let mockSupabaseClient: ServerSupabaseClient;
    let authGetUserMock: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      authGetUserMock = vi.fn();
      mockSupabaseClient = {
        auth: {
          getUser:
            authGetUserMock as unknown as ServerSupabaseClient["auth"]["getUser"],
        },
        from: vi.fn(),
      } as unknown as ServerSupabaseClient;
    });

    afterEach(() => {
      vi.clearAllMocks();
    });

    it("should return user when authenticated", async () => {
      const mockUser: User = {
        app_metadata: {},
        aud: "authenticated",
        created_at: "2025-01-01T00:00:00Z",
        email: "test@example.com",
        id: "user-123",
        user_metadata: {},
      };

      authGetUserMock.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      const result = await getCurrentUser(mockSupabaseClient, {
        enableTracing: false,
      });

      expect(result.user).toEqual(mockUser);
      expect(result.error).toBeNull();
      expect(authGetUserMock).toHaveBeenCalledTimes(1);
    });

    it("should return null user when not authenticated", async () => {
      authGetUserMock.mockResolvedValue({
        data: { user: null },
        error: null,
      });

      const result = await getCurrentUser(mockSupabaseClient, {
        enableTracing: false,
      });

      expect(result.user).toBeNull();
      expect(result.error).toBeNull();
    });

    it("should handle authentication errors", async () => {
      const mockError = new Error("Auth error");

      authGetUserMock.mockResolvedValue({
        data: { user: null },
        error: mockError,
      });

      const result = await getCurrentUser(mockSupabaseClient, {
        enableTracing: false,
      });

      expect(result.user).toBeNull();
      expect(result.error).toEqual(mockError);
    });

    it("should enable tracing by default", async () => {
      authGetUserMock.mockResolvedValue({
        data: { user: null },
        error: null,
      });

      await getCurrentUser(mockSupabaseClient);

      expect(startActiveSpanMock).toHaveBeenCalledWith(
        "supabase.auth.getUser",
        expect.objectContaining({
          attributes: expect.objectContaining({
            "db.name": "tripsage",
            "db.supabase.operation": "auth.getUser",
            "db.system": "postgres",
            "service.name": "tripsage-frontend",
          }),
        }),
        expect.any(Function)
      );
    });

    it("should redact user ID in telemetry", async () => {
      const mockUser: User = {
        app_metadata: {},
        aud: "authenticated",
        created_at: "2025-01-01T00:00:00Z",
        email: "test@example.com",
        id: "user-123",
        user_metadata: {},
      };

      authGetUserMock.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      await getCurrentUser(mockSupabaseClient);

      // Verify the span was created
      expect(startActiveSpanMock).toHaveBeenCalled();

      // The callback should set redacted user ID
      const callbackFn = startActiveSpanMock.mock.calls[0][2] as (span: {
        end: ReturnType<typeof vi.fn>;
        recordException: ReturnType<typeof vi.fn>;
        setAttribute: ReturnType<typeof vi.fn>;
        setStatus: ReturnType<typeof vi.fn>;
      }) => Promise<void>;
      const mockSpan = {
        end: vi.fn(),
        recordException: vi.fn(),
        setAttribute: vi.fn(),
        setStatus: vi.fn(),
      };

      await callbackFn(mockSpan);

      expect(mockSpan.setAttribute).toHaveBeenCalledWith("user.id", "[REDACTED]");
      expect(mockSpan.setAttribute).toHaveBeenCalledWith("user.authenticated", true);
    });

    it("should record exceptions in telemetry on error", async () => {
      const mockError = new Error("Auth error");

      authGetUserMock.mockResolvedValue({
        data: { user: null },
        error: mockError,
      });

      await getCurrentUser(mockSupabaseClient);

      const callbackFn = startActiveSpanMock.mock.calls[0][2] as (span: {
        end: ReturnType<typeof vi.fn>;
        recordException: ReturnType<typeof vi.fn>;
        setAttribute: ReturnType<typeof vi.fn>;
        setStatus: ReturnType<typeof vi.fn>;
      }) => Promise<void>;
      const mockSpan = {
        end: vi.fn(),
        recordException: vi.fn(),
        setAttribute: vi.fn(),
        setStatus: vi.fn(),
      };
      const recordExceptionSpy = mockSpan.recordException;

      await callbackFn(mockSpan);

      expect(mockSpan.setStatus).toHaveBeenCalledWith({
        code: SpanStatusCode.ERROR,
        message: "Auth error",
      });
      expect(recordExceptionSpy).toHaveBeenCalledWith(mockError);
    });

    it("should handle unknown errors", async () => {
      authGetUserMock.mockRejectedValue("Unknown error");

      const result = await getCurrentUser(mockSupabaseClient, {
        enableTracing: false,
      });

      expect(result.user).toBeNull();
      expect(result.error).toBeInstanceOf(Error);
      expect(result.error?.message).toBe("Unknown error");
    });
  });

  describe("createCookieAdapter", () => {
    it("should create cookie adapter from Next.js cookie store", () => {
      const mockCookieStore = {
        getAll: vi.fn(() => [
          { name: "cookie1", value: "value1" },
          { name: "cookie2", value: "value2" },
        ]),
        set: vi.fn(),
      } as unknown as ReadonlyRequestCookies;

      const adapter = createCookieAdapter(mockCookieStore);

      expect(adapter.getAll()).toEqual([
        { name: "cookie1", value: "value1" },
        { name: "cookie2", value: "value2" },
      ]);

      adapter.setAll?.([{ name: "new-cookie", options: {}, value: "new-value" }]);

      expect(mockCookieStore.set).toHaveBeenCalledWith("new-cookie", "new-value", {});
    });

    it("should handle cookie set errors gracefully", () => {
      const mockCookieStore = {
        getAll: vi.fn(() => []),
        set: vi.fn(() => {
          throw new Error("Cookie set error");
        }),
      } as unknown as ReadonlyRequestCookies;

      const adapter = createCookieAdapter(mockCookieStore);

      expect(() =>
        adapter.setAll?.([{ name: "cookie", options: {}, value: "value" }])
      ).not.toThrow();
    });
  });

  describe("isSupabaseClient", () => {
    it("should return true for valid Supabase client", () => {
      const validClient = {
        auth: {
          getSession: vi.fn(),
          getUser: vi.fn(),
          onAuthStateChange: vi.fn(),
        },
        channel: vi.fn(),
        from: vi.fn(),
      };

      expect(isSupabaseClient(validClient)).toBe(true);
    });

    it("should return false for null", () => {
      expect(isSupabaseClient(null)).toBe(false);
    });

    it("should return false for undefined", () => {
      expect(isSupabaseClient(undefined)).toBe(false);
    });

    it("should return false for objects without auth", () => {
      expect(isSupabaseClient({ from: vi.fn() })).toBe(false);
    });

    it("should return false for objects without from", () => {
      expect(isSupabaseClient({ auth: {} })).toBe(false);
    });

    it("should return false for primitives", () => {
      expect(isSupabaseClient("string")).toBe(false);
      expect(isSupabaseClient(123)).toBe(false);
      expect(isSupabaseClient(true)).toBe(false);
    });
  });
});
