import { type NextRequest, NextResponse } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock @supabase/ssr using vi.hoisted to ensure proper hoisting
const mockCreateServerClient = vi.hoisted(() => vi.fn());

vi.mock("@supabase/ssr", () => ({
  createServerClient: mockCreateServerClient,
}));

import { createServerClient } from "@supabase/ssr";
import { updateSession } from "../middleware";

// Define proper types for cookie handling
interface Cookie {
  name: string;
  value: string;
}

interface CookieWithOptions extends Cookie {
  options?: Record<string, unknown>;
}

interface MockCookies {
  getAll: ReturnType<typeof vi.fn>;
  set: ReturnType<typeof vi.fn>;
  get: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
  has: ReturnType<typeof vi.fn>;
  forEach: ReturnType<typeof vi.fn>;
  clear: ReturnType<typeof vi.fn>;
}

// Helper function to create a properly mocked NextRequest
function createMockNextRequest(url: string, headers: Record<string, string> = {}) {
  const mockCookies: MockCookies = {
    getAll: vi.fn(() => []),
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
  } as unknown as NextRequest;

  return request;
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
    const mockCookies: Cookie[] = [
      { name: "sb-access-token", value: "token123" },
      { name: "sb-refresh-token", value: "refresh123" },
    ];
    vi.mocked(mockRequest.cookies.getAll).mockReturnValue(mockCookies);

    // Define Supabase auth types
    interface SupabaseAuth {
      getUser: ReturnType<typeof vi.fn>;
    }

    interface MockSupabase {
      auth: SupabaseAuth;
    }

    // Mock Supabase client
    const mockSupabase: MockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: mockUser },
          error: null,
        }),
      },
    };

    interface CookieHandlers {
      getAll: () => Cookie[];
      setAll: (cookies: CookieWithOptions[]) => void;
    }

    let capturedCookieHandlers: CookieHandlers | null = null;
    mockCreateServerClient.mockImplementation((_url, _key, options) => {
      capturedCookieHandlers = options.cookies as CookieHandlers;
      return mockSupabase as unknown as ReturnType<typeof createServerClient>;
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
    expect(capturedCookieHandlers).toBeDefined();
    const getAllResult = capturedCookieHandlers!.getAll();
    expect(getAllResult).toEqual(mockCookies);

    // Test setAll handler - just verify it can be called without errors
    expect(() => {
      capturedCookieHandlers!.setAll([
        { name: "test", value: "value", options: { httpOnly: true } },
      ]);
    }).not.toThrow();
  });

  it("should handle missing user gracefully", async () => {
    const mockRequest = createMockNextRequest("http://localhost:3000/dashboard");

    vi.mocked(mockRequest.cookies.getAll).mockReturnValue([]);

    const mockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: null },
          error: null,
        }),
      },
    };

    mockCreateServerClient.mockReturnValue(
      mockSupabase as unknown as ReturnType<typeof createServerClient>
    );

    const supabaseResponse = await updateSession(mockRequest);

    expect(mockSupabase.auth.getUser).toHaveBeenCalled();
    expect(supabaseResponse).toBeInstanceOf(NextResponse);
  });

  it("should handle auth errors gracefully", async () => {
    const mockRequest = createMockNextRequest("http://localhost:3000/dashboard");

    vi.mocked(mockRequest.cookies.getAll).mockReturnValue([]);

    const mockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: null },
          error: { message: "Invalid token" },
        }),
      },
    };

    mockCreateServerClient.mockReturnValue(
      mockSupabase as unknown as ReturnType<typeof createServerClient>
    );

    const supabaseResponse = await updateSession(mockRequest);

    expect(mockSupabase.auth.getUser).toHaveBeenCalled();
    expect(supabaseResponse).toBeInstanceOf(NextResponse);
  });

  it("should handle request with multiple cookies", async () => {
    const mockRequest = createMockNextRequest("http://localhost:3000/api/data");

    const mockCookies: Cookie[] = [
      { name: "sb-access-token", value: "access123" },
      { name: "sb-refresh-token", value: "refresh123" },
      { name: "other-cookie", value: "other-value" },
    ];

    vi.mocked(mockRequest.cookies.getAll).mockReturnValue(mockCookies);

    const mockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: { id: "user123" } },
          error: null,
        }),
      },
    };

    interface CookieHandlers {
      getAll: () => Cookie[];
      setAll: (cookies: CookieWithOptions[]) => void;
    }

    let capturedCookieHandlers: CookieHandlers | null = null;
    mockCreateServerClient.mockImplementation((_url, _key, options) => {
      capturedCookieHandlers = options.cookies as CookieHandlers;
      return mockSupabase as unknown as ReturnType<typeof createServerClient>;
    });

    const supabaseResponse = await updateSession(mockRequest);

    expect(supabaseResponse).toBeInstanceOf(NextResponse);
    expect(mockSupabase.auth.getUser).toHaveBeenCalled();

    // Test that cookie handlers work with multiple cookies
    expect(capturedCookieHandlers).toBeDefined();
    const getAllResult = capturedCookieHandlers!.getAll();
    expect(getAllResult).toEqual(mockCookies);
  });
});
