import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { updateSession } from "../middleware";

// Mock @supabase/ssr
vi.mock("@supabase/ssr", () => ({
  createServerClient: vi.fn(),
}));

// Helper function to create a properly mocked NextRequest
function createMockNextRequest(url: string, headers: Record<string, string> = {}) {
  const mockCookies = {
    getAll: vi.fn().mockReturnValue([]),
    set: vi.fn(),
    get: vi.fn(),
    delete: vi.fn(),
    has: vi.fn(),
    forEach: vi.fn(),
    clear: vi.fn(),
  };

  const request = {
    url,
    nextUrl: new URL(url),
    headers: new Headers(headers),
    cookies: mockCookies,
  } as any;

  return request as NextRequest;
}

describe("Middleware - updateSession", () => {
  const mockSupabaseUrl = "https://test.supabase.co";
  const mockSupabaseAnonKey = "test-anon-key";

  beforeEach(() => {
    vi.resetAllMocks();
    process.env.NEXT_PUBLIC_SUPABASE_URL = mockSupabaseUrl;
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = mockSupabaseAnonKey;
  });

  it("should refresh session and return updated response", async () => {
    const mockUser = { id: "user123", email: "test@example.com" };
    const mockRequest = createMockNextRequest("http://localhost:3000/dashboard");

    // Mock cookies
    const mockCookies = [
      { name: "sb-access-token", value: "token123" },
      { name: "sb-refresh-token", value: "refresh123" },
    ];
    (mockRequest.cookies.getAll as any).mockReturnValue(mockCookies);

    // Mock Supabase client
    const mockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: mockUser },
          error: null,
        }),
      },
    };

    let capturedCookieHandlers: any = null;
    vi.mocked(createServerClient).mockImplementation((url, key, options) => {
      capturedCookieHandlers = options.cookies;
      return mockSupabase as any;
    });

    const supabaseResponse = await updateSession(mockRequest);

    // Verify Supabase client was created
    expect(createServerClient).toHaveBeenCalledWith(
      mockSupabaseUrl,
      mockSupabaseAnonKey,
      expect.objectContaining({
        cookies: expect.any(Object),
      })
    );

    // Verify user was fetched
    expect(mockSupabase.auth.getUser).toHaveBeenCalled();

    // Verify response has cookies set
    expect(supabaseResponse).toBeInstanceOf(NextResponse);

    // Test cookie handlers
    const getAllResult = capturedCookieHandlers.getAll();
    expect(getAllResult).toEqual(mockCookies);

    // Test setAll handler - just verify it can be called without errors
    expect(() => {
      capturedCookieHandlers.setAll([
        { name: "test", value: "value", options: { httpOnly: true } },
      ]);
    }).not.toThrow();
  });

  it("should handle missing user gracefully", async () => {
    const mockRequest = createMockNextRequest("http://localhost:3000/dashboard");

    (mockRequest.cookies.getAll as any).mockReturnValue([]);

    const mockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: null },
          error: null,
        }),
      },
    };

    vi.mocked(createServerClient).mockReturnValue(mockSupabase as any);

    const supabaseResponse = await updateSession(mockRequest);

    expect(mockSupabase.auth.getUser).toHaveBeenCalled();
    expect(supabaseResponse).toBeInstanceOf(NextResponse);
  });

  it("should handle auth errors gracefully", async () => {
    const mockRequest = createMockNextRequest("http://localhost:3000/dashboard");

    (mockRequest.cookies.getAll as any).mockReturnValue([]);

    const mockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: null },
          error: { message: "Invalid token" },
        }),
      },
    };

    vi.mocked(createServerClient).mockReturnValue(mockSupabase as any);

    const supabaseResponse = await updateSession(mockRequest);

    expect(mockSupabase.auth.getUser).toHaveBeenCalled();
    expect(supabaseResponse).toBeInstanceOf(NextResponse);
  });

  it("should handle request with multiple cookies", async () => {
    const mockRequest = createMockNextRequest("http://localhost:3000/api/data");

    const mockCookies = [
      { name: "sb-access-token", value: "access123" },
      { name: "sb-refresh-token", value: "refresh123" },
      { name: "other-cookie", value: "other-value" },
    ];

    (mockRequest.cookies.getAll as any).mockReturnValue(mockCookies);

    const mockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: { id: "user123" } },
          error: null,
        }),
      },
    };

    let capturedCookieHandlers: any = null;
    vi.mocked(createServerClient).mockImplementation((url, key, options) => {
      capturedCookieHandlers = options.cookies;
      return mockSupabase as any;
    });

    const supabaseResponse = await updateSession(mockRequest);

    expect(supabaseResponse).toBeInstanceOf(NextResponse);
    expect(mockSupabase.auth.getUser).toHaveBeenCalled();

    // Test that cookie handlers work with multiple cookies
    const getAllResult = capturedCookieHandlers.getAll();
    expect(getAllResult).toEqual(mockCookies);
  });
});
