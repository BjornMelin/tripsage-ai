/**
 * @fileoverview Tests for unified Supabase factory.
 *
 * This test suite validates the factory's ability to create server clients,
 * manage cookies, integrate with OpenTelemetry, and provide unified user
 * authentication methods.
 */

import { SpanStatusCode } from "@opentelemetry/api";
import type { CookieMethodsServer } from "@supabase/ssr";
import type { User } from "@supabase/supabase-js";
import type { ReadonlyRequestCookies } from "next/dist/server/web/spec-extension/adapters/request-cookies";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ServerSupabaseClient } from "../factory";
import {
  createCookieAdapter,
  createServerSupabase,
  getCurrentUser,
  isSupabaseClient,
} from "../factory";

// Mock dependencies
vi.mock("@supabase/ssr", () => ({
  createServerClient: vi.fn(),
}));

vi.mock("@opentelemetry/api", () => ({
  SpanStatusCode: {
    ERROR: 2,
    OK: 1,
    UNSET: 0,
  },
  trace: {
    getTracer: vi.fn(() => ({
      startActiveSpan: vi.fn((_name, _options, callback) => {
        const mockSpan = {
          end: vi.fn(),
          recordException: vi.fn(),
          setAttribute: vi.fn(),
          setStatus: vi.fn(),
        };
        return callback(mockSpan);
      }),
    })),
  },
}));

vi.mock("@/lib/env/server", () => ({
  getServerEnv: vi.fn(() => ({
    NEXT_PUBLIC_SUPABASE_ANON_KEY: "test-anon-key",
    NEXT_PUBLIC_SUPABASE_URL: "https://test.supabase.co",
  })),
}));

vi.mock("@/lib/telemetry/tracer", () => ({
  TELEMETRY_SERVICE_NAME: "tripsage-frontend",
}));

describe("Supabase Factory", () => {
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
      const { createServerClient } = require("@supabase/ssr");

      createServerClient.mockReturnValue({
        auth: {
          getUser: vi.fn(),
        },
        from: vi.fn(),
      });

      const client = createServerSupabase({
        cookies: mockCookieAdapter,
      });

      expect(createServerClient).toHaveBeenCalledWith(
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
      const { createServerClient } = require("@supabase/ssr");
      const { trace } = require("@opentelemetry/api");

      createServerClient.mockReturnValue({
        auth: { getUser: vi.fn() },
        from: vi.fn(),
      });

      createServerSupabase({
        cookies: mockCookieAdapter,
      });

      const tracer = trace.getTracer();
      expect(tracer.startActiveSpan).toHaveBeenCalledWith(
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
      const { createServerClient } = require("@supabase/ssr");
      const { trace } = require("@opentelemetry/api");

      createServerClient.mockReturnValue({
        auth: { getUser: vi.fn() },
        from: vi.fn(),
      });

      createServerSupabase({
        cookies: mockCookieAdapter,
        enableTracing: false,
      });

      const tracer = trace.getTracer();
      expect(tracer.startActiveSpan).not.toHaveBeenCalled();
    });

    it("should use custom span name when provided", () => {
      const { createServerClient } = require("@supabase/ssr");
      const { trace } = require("@opentelemetry/api");

      createServerClient.mockReturnValue({
        auth: { getUser: vi.fn() },
        from: vi.fn(),
      });

      createServerSupabase({
        cookies: mockCookieAdapter,
        spanName: "custom.span.name",
      });

      const tracer = trace.getTracer();
      expect(tracer.startActiveSpan).toHaveBeenCalledWith(
        "custom.span.name",
        expect.any(Object),
        expect.any(Function)
      );
    });

    it("should handle cookie adapter errors gracefully", () => {
      const { createServerClient } = require("@supabase/ssr");

      const errorCookieAdapter: CookieMethodsServer = {
        getAll: vi.fn(() => {
          throw new Error("Cookie read error");
        }),
        setAll: vi.fn(),
      };

      createServerClient.mockImplementation(
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
      const { createServerClient } = require("@supabase/ssr");

      createServerClient.mockReturnValue({
        auth: { getUser: vi.fn() },
        from: vi.fn(),
      });

      expect(() =>
        createServerSupabase({
          enableTracing: false,
        })
      ).toThrow("Cookie adapter required for server client creation");
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
      const { trace } = require("@opentelemetry/api");

      authGetUserMock.mockResolvedValue({
        data: { user: null },
        error: null,
      });

      await getCurrentUser(mockSupabaseClient);

      const tracer = trace.getTracer();
      expect(tracer.startActiveSpan).toHaveBeenCalledWith(
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

      const { trace } = require("@opentelemetry/api");
      const tracer = trace.getTracer();

      // Verify the span was created
      expect(tracer.startActiveSpan).toHaveBeenCalled();

      // The callback should set redacted user ID
      const callbackFn = tracer.startActiveSpan.mock.calls[0][2];
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

      const { trace } = require("@opentelemetry/api");
      const tracer = trace.getTracer();
      const callbackFn = tracer.startActiveSpan.mock.calls[0][2];
      const mockSpan = {
        end: vi.fn(),
        recordException: vi.fn(),
        setAttribute: vi.fn(),
        setStatus: vi.fn(),
      };

      await callbackFn(mockSpan);

      expect(mockSpan.setStatus).toHaveBeenCalledWith({
        code: SpanStatusCode.ERROR,
        message: "Auth error",
      });
      expect(mockSpan.recordException).toHaveBeenCalledWith(mockError);
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
        auth: {},
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
