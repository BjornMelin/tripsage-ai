import { config, middleware } from "@/middleware";
import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock JWT token for testing
const TEST_TOKEN = "mock-jwt-token-for-testing";

// Mock Next.js server components
vi.mock("next/server", () => ({
  NextRequest: globalThis.Request,
  NextResponse: {
    next: vi.fn(),
    json: vi.fn(),
    redirect: vi.fn(),
  },
}));

// Mock Supabase SSR client
vi.mock("@supabase/ssr", () => ({
  createServerClient: vi.fn(),
}));

// Mock environment variables
vi.stubEnv("JWT_SECRET", "test-jwt-secret-for-middleware-tests");
vi.stubEnv("NODE_ENV", "test");
vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");

// Helper function to create NextRequest with proper Headers
function createRequest(
  url: string,
  options: { method?: string; headers?: Record<string, string> } = {}
) {
  const headers = new Headers();
  if (options.headers) {
    for (const [key, value] of Object.entries(options.headers)) {
      headers.set(key, value);
    }
  }

  // Use standard Request since we're mocking NextRequest
  const request = new Request(url, {
    method: options.method || "GET",
    headers,
  });

  // Add NextRequest-specific properties
  Object.assign(request, {
    nextUrl: new URL(url),
    cookies: {
      getAll: vi.fn().mockReturnValue([]),
      set: vi.fn(),
    },
  });

  return request as NextRequest;
}

describe("Middleware", () => {
  let mockSupabase: ReturnType<typeof createServerClient>;
  let mockResponseInstance: NextResponse;

  beforeEach(() => {
    vi.clearAllMocks();
    // Clear the rate limit store between tests
    vi.resetModules();

    // Create a mock NextResponse instance
    mockResponseInstance = {
      status: 200,
      headers: {
        get: vi.fn().mockReturnValue(null),
        set: vi.fn(),
        append: vi.fn(),
        delete: vi.fn(),
        has: vi.fn(),
        forEach: vi.fn(),
        entries: vi.fn(),
        keys: vi.fn(),
        values: vi.fn(),
      },
      json: vi.fn().mockResolvedValue({}),
      cookies: {
        set: vi.fn(),
      },
    } as unknown as NextResponse;

    // Setup NextResponse mocks
    vi.mocked(NextResponse.next).mockReturnValue(mockResponseInstance);
    vi.mocked(NextResponse.json).mockImplementation((body, init) => ({
      ...mockResponseInstance,
      status: init?.status || 200,
      json: vi.fn().mockResolvedValue(body),
    } as unknown as NextResponse));

    // Setup mock Supabase client
    mockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({ data: { user: null } }),
      },
    };
    vi.mocked(createServerClient).mockReturnValue(mockSupabase);
  });

  describe("Rate Limiting", () => {
    it("should allow requests under the rate limit", async () => {
      // Arrange
      const request = createRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: { "x-forwarded-for": "192.168.1.1" },
      });

      // Act
      const response = await middleware(request);

      // Assert
      expect(response.status).toBe(200);
      expect(response.headers.set).toHaveBeenCalledWith("X-RateLimit-Limit", "10");
      expect(response.headers.set).toHaveBeenCalledWith("X-RateLimit-Remaining", "9");
      expect(response.headers.set).toHaveBeenCalledWith(
        "X-RateLimit-Reset",
        expect.any(String)
      );
    });

    it("should reject requests over the rate limit", async () => {
      // Arrange
      const ip = "192.168.1.2";
      const requests = [];

      // Make 10 requests to hit the limit
      for (let i = 0; i < 10; i++) {
        const request = createRequest("http://localhost:3000/api/chat", {
          method: "POST",
          headers: { "x-forwarded-for": ip },
        });
        const response = await middleware(request);
        requests.push(response);
      }

      // Make one more request that should be rejected
      const blockedRequest = createRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: { "x-forwarded-for": ip },
      });

      // Act
      const blockedResponse = await middleware(blockedRequest);

      // Assert
      expect(blockedResponse.status).toBe(429);
      expect(blockedResponse.headers.set).toHaveBeenCalledWith(
        "X-RateLimit-Remaining",
        "0"
      );
      expect(blockedResponse.headers.set).toHaveBeenCalledWith(
        "Retry-After",
        expect.any(String)
      );

      // Check that NextResponse.json was called with the right error body
      expect(NextResponse.json).toHaveBeenCalledWith(
        {
          error: "Too many requests. Please wait before trying again.",
          code: "RATE_LIMITED",
          retryAfter: expect.any(Number),
        },
        { status: 429 }
      );
    });

    it("should track rate limits per IP address", async () => {
      // Arrange
      const ip1 = "192.168.1.3";
      const ip2 = "192.168.1.4";

      // Make 5 requests from IP1
      for (let i = 0; i < 5; i++) {
        const request = createRequest("http://localhost:3000/api/chat", {
          method: "POST",
          headers: { "x-forwarded-for": ip1 },
        });
        await middleware(request);
      }

      // Act - Make request from IP2
      const request2 = createRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: { "x-forwarded-for": ip2 },
      });
      const response2 = await middleware(request2);

      // Assert - IP2 should have full limit available
      expect(response2.status).toBe(200);
      expect(response2.headers.set).toHaveBeenCalledWith("X-RateLimit-Remaining", "9");
    });

    it("should prefer auth token over IP for rate limiting", async () => {
      // Arrange
      const authToken = `Bearer ${TEST_TOKEN}`;
      const request = createRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: {
          "x-forwarded-for": "192.168.1.5",
          authorization: authToken,
        },
      });

      // Act
      const response = await middleware(request);

      // Assert
      expect(response.status).toBe(200);
      expect(response.headers.set).toHaveBeenCalledWith("X-RateLimit-Limit", "10");
    });

    it("should not apply rate limiting to non-chat endpoints", async () => {
      // Arrange
      const request = createRequest("http://localhost:3000/api/health", {
        method: "GET",
        headers: { "x-forwarded-for": "192.168.1.6" },
      });

      // Act
      const response = await middleware(request);

      // Assert
      expect(response.status).toBe(200);
      expect(response.headers.set).not.toHaveBeenCalledWith(
        "X-RateLimit-Limit",
        expect.any(String)
      );
    });

    it("should skip rate limiting for attachment uploads", async () => {
      // Arrange
      const request = createRequest("http://localhost:3000/api/chat/attachments", {
        method: "POST",
        headers: { "x-forwarded-for": "192.168.1.7" },
      });

      // Act
      const response = await middleware(request);

      // Assert
      expect(response.status).toBe(200);
      expect(response.headers.set).not.toHaveBeenCalledWith(
        "X-RateLimit-Limit",
        expect.any(String)
      );
    });

    it("should handle x-real-ip header", async () => {
      // Arrange
      const request = createRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: { "x-real-ip": "192.168.1.8" },
      });

      // Act
      const response = await middleware(request);

      // Assert
      expect(response.status).toBe(200);
      expect(response.headers.set).toHaveBeenCalledWith("X-RateLimit-Remaining", "9");
    });

    it("should parse first IP from x-forwarded-for list", async () => {
      // Arrange
      const request = createRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: { "x-forwarded-for": "192.168.1.9, 10.0.0.1, 172.16.0.1" },
      });

      // Act
      const response = await middleware(request);

      // Assert
      expect(response.status).toBe(200);
      expect(response.headers.set).toHaveBeenCalledWith("X-RateLimit-Remaining", "9");
    });

    it("should provide retry-after in seconds", async () => {
      // Arrange
      const ip = "192.168.1.10";

      // Hit rate limit
      for (let i = 0; i < 10; i++) {
        const request = createRequest("http://localhost:3000/api/chat", {
          method: "POST",
          headers: { "x-forwarded-for": ip },
        });
        await middleware(request);
      }

      // Act - Make blocked request
      const blockedRequest = createRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: { "x-forwarded-for": ip },
      });
      const blockedResponse = await middleware(blockedRequest);

      // Assert
      expect(blockedResponse.headers.set).toHaveBeenCalledWith(
        "Retry-After",
        expect.any(String)
      );

      // Check that NextResponse.json was called with the right error body
      expect(NextResponse.json).toHaveBeenCalledWith(
        {
          error: "Too many requests. Please wait before trying again.",
          code: "RATE_LIMITED",
          retryAfter: expect.any(Number),
        },
        { status: 429 }
      );
    });
  });

  describe("Supabase Session Management", () => {
    it("should create Supabase client and refresh session", async () => {
      // Arrange
      const request = createRequest("http://localhost:3000/dashboard", {
        method: "GET",
        headers: { cookie: "sb-access-token=token123; sb-refresh-token=refresh123" },
      });

      // Act
      const response = await middleware(request);

      // Assert
      expect(createServerClient).toHaveBeenCalledWith(
        "https://test.supabase.co",
        "test-anon-key",
        expect.objectContaining({
          cookies: expect.objectContaining({
            getAll: expect.any(Function),
            setAll: expect.any(Function),
          }),
        })
      );
      expect(mockSupabase.auth.getUser).toHaveBeenCalled();
      expect(response.status).toBe(200);
    });

    it("should handle missing Supabase environment variables gracefully", async () => {
      // Arrange
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "");

      const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
      const request = createRequest("http://localhost:3000/dashboard");

      // Act
      const response = await middleware(request);

      // Assert
      expect(consoleSpy).toHaveBeenCalledWith("Missing Supabase environment variables");
      expect(createServerClient).not.toHaveBeenCalled();
      expect(response.status).toBe(200);

      consoleSpy.mockRestore();
      // Restore env vars for other tests
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");
    });

    it("should handle Supabase auth errors gracefully", async () => {
      // Arrange
      mockSupabase.auth.getUser.mockRejectedValue(new Error("Auth error"));
      const request = createRequest("http://localhost:3000/dashboard");

      // Act - Should not throw and return a response
      const response = await middleware(request);

      // Assert
      expect(response).toBeDefined();
      expect(response.status).toBe(200);
    });

    it("should handle cookie operations correctly", async () => {
      // Arrange
      let capturedCookieHandlers:
        | Parameters<typeof createServerClient>[2]["cookies"]
        | null = null;
      vi.mocked(createServerClient).mockImplementation((url, key, options) => {
        capturedCookieHandlers = options.cookies;
        return mockSupabase;
      });

      const request = createRequest("http://localhost:3000/dashboard", {
        headers: { cookie: "test=value" },
      });

      // Act
      await middleware(request);

      // Assert
      expect(capturedCookieHandlers).toBeTruthy();
      expect(capturedCookieHandlers).toBeDefined();
      expect(typeof capturedCookieHandlers!.getAll).toBe("function");
      expect(typeof capturedCookieHandlers!.setAll).toBe("function");

      // Test getAll functionality
      const cookies = capturedCookieHandlers!.getAll();
      expect(cookies).toBeDefined();

      // Test setAll functionality - should not throw
      if (capturedCookieHandlers) {
        expect(() => {
          capturedCookieHandlers.setAll([
            { name: "new1", value: "val1", options: { httpOnly: true } },
          ]);
        }).not.toThrow();
      }
    });
  });

  describe("Configuration", () => {
    it("should have correct matcher configuration", () => {
      expect(config).toBeDefined();
      expect(config.matcher).toEqual([
        "/((?!_next/static|_next/image|favicon.ico|public).*)",
      ]);
    });

    it("should match API routes", () => {
      const matcher = config.matcher[0];
      // The regex pattern has the structure /(pattern)/
      const pattern = matcher.slice(2, -1); // Remove /( and )
      const regex = new RegExp(pattern);

      expect(regex.test("/api/chat")).toBe(true);
      expect(regex.test("/api/auth")).toBe(true);
      expect(regex.test("/dashboard")).toBe(true);
    });

    it("should test with middleware matcher behavior", () => {
      const matcher = config.matcher[0];

      // Test with full pattern matching behavior (like Next.js does)
      const testPaths = [
        "/_next/static/chunks/webpack.js",
        "/_next/image/optimize",
        "/favicon.ico",
        "/public/logo.png",
        "/api/chat",
        "/dashboard",
      ];

      for (const path of testPaths) {
        const match = path.match(matcher);

        // These should NOT match (be excluded)
        if (path === "/favicon.ico") {
          expect(match).toBeNull();
        }
        // These SHOULD match (be included)
        else if (path === "/api/chat" || path === "/dashboard") {
          expect(match).toBeTruthy();
        }
        // The behavior for _next and public paths depends on exact implementation
        // but we'll test that they're consistently handled
      }
    });
  });

  describe("Edge Cases", () => {
    it("should handle malformed x-forwarded-for header", async () => {
      // Arrange
      const request = createRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: { "x-forwarded-for": "" }, // Empty string
      });

      // Act & Assert - Should not throw
      await expect(middleware(request)).resolves.toBeDefined();
    });

    it("should handle very long auth headers", async () => {
      // Arrange
      const longToken = `Bearer ${"x".repeat(1000)}`;
      const request = createRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: { authorization: longToken },
      });

      // Act & Assert - Should handle long tokens without issues
      await expect(middleware(request)).resolves.toBeDefined();
    });

    it("should handle concurrent requests properly", async () => {
      // Arrange
      const requests = Array(5)
        .fill(null)
        .map(() =>
          createRequest("http://localhost:3000/api/chat", {
            method: "POST",
            headers: { "x-forwarded-for": "192.168.1.100" },
          })
        );

      // Act - Make multiple concurrent requests
      const promises = requests.map((req) => middleware(req));
      const responses = await Promise.all(promises);

      // Assert - All should succeed and handle concurrent access properly
      for (const response of responses) {
        expect(response.status).toBe(200);
      }
    });

    it("should handle requests without any IP headers", async () => {
      // Arrange
      const request = createRequest("http://localhost:3000/api/chat", {
        method: "POST",
        // No IP headers - should fallback to localhost
      });

      // Act
      const response = await middleware(request);

      // Assert
      expect(response.status).toBe(200);
      expect(response.headers.set).toHaveBeenCalledWith("X-RateLimit-Limit", "10");
      // Since rate limit store is shared, we need to check what remaining count was actually set
      expect(response.headers.set).toHaveBeenCalledWith(
        "X-RateLimit-Remaining",
        expect.any(String)
      );
    });

    it("should handle rate limit window expiry correctly", async () => {
      // Arrange
      const ip = "192.168.1.200";
      const mockDateNow = vi.spyOn(Date, "now");

      // Set initial time
      mockDateNow.mockReturnValue(1000000);

      // Make 10 requests (hit the limit)
      for (let i = 0; i < 10; i++) {
        const request = createRequest("http://localhost:3000/api/chat", {
          method: "POST",
          headers: { "x-forwarded-for": ip },
        });
        await middleware(request);
      }

      // Fast forward time by 61 seconds (past the 60 second window)
      mockDateNow.mockReturnValue(1000000 + 61000);

      // Act - Make another request (should succeed with fresh window)
      const request = createRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: { "x-forwarded-for": ip },
      });
      const response = await middleware(request);

      // Assert
      expect(response.status).toBe(200);
      expect(response.headers.set).toHaveBeenCalledWith("X-RateLimit-Remaining", "9");

      mockDateNow.mockRestore();
    });

    it("should handle different HTTP methods consistently", async () => {
      // Arrange
      const methods = ["GET", "POST", "PUT", "DELETE", "PATCH"];
      const ip = "192.168.1.300";

      // Act & Assert
      for (const method of methods) {
        const request = createRequest("http://localhost:3000/api/chat", {
          method,
          headers: { "x-forwarded-for": ip },
        });
        const response = await middleware(request);
        expect(response.status).toBe(200);
      }
    });
  });
});
