import { middleware } from "@/middleware";
import { NextRequest, NextResponse } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock JWT token for testing
const TEST_TOKEN = "mock-jwt-token-for-testing";

// Mock environment variables
vi.stubEnv("JWT_SECRET", "test-jwt-secret-for-middleware-tests");
vi.stubEnv("NODE_ENV", "test");

describe("Rate Limiting Middleware", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clear the rate limit store between tests
    vi.resetModules();
  });

  it("should allow requests under the rate limit", async () => {
    // Arrange
    const request = new NextRequest("http://localhost:3000/api/chat", {
      method: "POST",
      headers: {
        "x-forwarded-for": "192.168.1.1",
      },
    });

    // Act
    const response = await middleware(request);

    // Assert
    expect(response.status).toBe(200);
    expect(response.headers.get("X-RateLimit-Limit")).toBe("10");
    expect(response.headers.get("X-RateLimit-Remaining")).toBe("9");
    expect(response.headers.get("X-RateLimit-Reset")).toBeTruthy();
  });

  it("should reject requests over the rate limit", async () => {
    // Arrange
    const ip = "192.168.1.2";
    const requests = [];

    // Make 10 requests to hit the limit
    for (let i = 0; i < 10; i++) {
      const request = new NextRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: {
          "x-forwarded-for": ip,
        },
      });
      const response = await middleware(request);
      requests.push(response);
    }

    // Make one more request that should be rejected
    const blockedRequest = new NextRequest("http://localhost:3000/api/chat", {
      method: "POST",
      headers: {
        "x-forwarded-for": ip,
      },
    });

    // Act
    const blockedResponse = await middleware(blockedRequest);

    // Assert
    expect(blockedResponse.status).toBe(429);
    expect(blockedResponse.headers.get("X-RateLimit-Remaining")).toBe("0");
    expect(blockedResponse.headers.get("Retry-After")).toBeTruthy();

    const body = await blockedResponse.json();
    expect(body.error).toBe("Too many requests. Please wait before trying again.");
    expect(body.code).toBe("RATE_LIMITED");
  });

  it("should track rate limits per IP address", async () => {
    // Arrange
    const ip1 = "192.168.1.3";
    const ip2 = "192.168.1.4";

    // Make 5 requests from IP1
    for (let i = 0; i < 5; i++) {
      const request = new NextRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: {
          "x-forwarded-for": ip1,
        },
      });
      await middleware(request);
    }

    // Act - Make request from IP2
    const request2 = new NextRequest("http://localhost:3000/api/chat", {
      method: "POST",
      headers: {
        "x-forwarded-for": ip2,
      },
    });
    const response2 = await middleware(request2);

    // Assert - IP2 should have full limit available
    expect(response2.status).toBe(200);
    expect(response2.headers.get("X-RateLimit-Remaining")).toBe("9");
  });

  it("should prefer auth token over IP for rate limiting", async () => {
    // Arrange
    const authToken = "Bearer " + TEST_TOKEN;
    const request = new NextRequest("http://localhost:3000/api/chat", {
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
    expect(response.headers.get("X-RateLimit-Limit")).toBe("10");
  });

  it("should not apply rate limiting to non-chat endpoints", async () => {
    // Arrange
    const request = new NextRequest("http://localhost:3000/api/health", {
      method: "GET",
      headers: {
        "x-forwarded-for": "192.168.1.6",
      },
    });

    // Act
    const response = await middleware(request);

    // Assert
    expect(response.status).toBe(200);
    expect(response.headers.get("X-RateLimit-Limit")).toBeNull();
  });

  it("should skip rate limiting for attachment uploads", async () => {
    // Arrange
    const request = new NextRequest("http://localhost:3000/api/chat/attachments", {
      method: "POST",
      headers: {
        "x-forwarded-for": "192.168.1.7",
      },
    });

    // Act
    const response = await middleware(request);

    // Assert
    expect(response.status).toBe(200);
    expect(response.headers.get("X-RateLimit-Limit")).toBeNull();
  });

  it("should handle x-real-ip header", async () => {
    // Arrange
    const request = new NextRequest("http://localhost:3000/api/chat", {
      method: "POST",
      headers: {
        "x-real-ip": "192.168.1.8",
      },
    });

    // Act
    const response = await middleware(request);

    // Assert
    expect(response.status).toBe(200);
    expect(response.headers.get("X-RateLimit-Remaining")).toBe("9");
  });

  it("should parse first IP from x-forwarded-for list", async () => {
    // Arrange
    const request = new NextRequest("http://localhost:3000/api/chat", {
      method: "POST",
      headers: {
        "x-forwarded-for": "192.168.1.9, 10.0.0.1, 172.16.0.1",
      },
    });

    // Act
    const response = await middleware(request);

    // Assert
    expect(response.status).toBe(200);
    expect(response.headers.get("X-RateLimit-Remaining")).toBe("9");
  });

  it("should provide retry-after in seconds", async () => {
    // Arrange
    const ip = "192.168.1.10";

    // Hit rate limit
    for (let i = 0; i < 10; i++) {
      const request = new NextRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: {
          "x-forwarded-for": ip,
        },
      });
      await middleware(request);
    }

    // Act - Make blocked request
    const blockedRequest = new NextRequest("http://localhost:3000/api/chat", {
      method: "POST",
      headers: {
        "x-forwarded-for": ip,
      },
    });
    const blockedResponse = await middleware(blockedRequest);

    // Assert
    const retryAfter = blockedResponse.headers.get("Retry-After");
    expect(retryAfter).toBeTruthy();
    expect(Number.parseInt(retryAfter!)).toBeGreaterThan(0);
    expect(Number.parseInt(retryAfter!)).toBeLessThanOrEqual(60);

    const body = await blockedResponse.json();
    expect(body.retryAfter).toBeTruthy();
    expect(body.retryAfter).toBeGreaterThan(0);
  });
});
