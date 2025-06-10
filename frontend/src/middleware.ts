import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";

// Simple in-memory rate limiter with automatic cleanup
class RateLimiter {
  private store = new Map<string, { count: number; resetTime: number }>();
  private cleanupTimer: NodeJS.Timeout | null = null;

  constructor() {
    // Only set up cleanup in non-serverless environments
    if (typeof process !== "undefined" && process.env.NODE_ENV !== "production") {
      this.setupCleanup();
    }
  }

  private setupCleanup() {
    this.cleanupTimer = setInterval(() => {
      const now = Date.now();
      for (const [key, value] of this.store.entries()) {
        if (now > value.resetTime) {
          this.store.delete(key);
        }
      }
    }, 60000); // Clean up every minute
  }

  check(identifier: string, limit = 10, windowMs = 60000) {
    const now = Date.now();
    const record = this.store.get(identifier);
    const resetTime = now + windowMs;

    if (!record || now > record.resetTime) {
      this.store.set(identifier, { count: 1, resetTime });
      return { success: true, limit, remaining: limit - 1, reset: resetTime };
    }

    if (record.count >= limit) {
      return { success: false, limit, remaining: 0, reset: record.resetTime };
    }

    record.count++;
    return {
      success: true,
      limit,
      remaining: limit - record.count,
      reset: record.resetTime,
    };
  }

  cleanup() {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
    }
  }
}

const rateLimiter = new RateLimiter();

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({
    request,
  });

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    console.warn("Missing Supabase environment variables");
    return supabaseResponse;
  }

  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        supabaseResponse = NextResponse.next({
          request,
        });
        cookiesToSet.forEach(({ name, value, options }) =>
          supabaseResponse.cookies.set(name, value, options)
        );
      },
    },
  });

  // Refresh session if expired - required for Server Components
  try {
    await supabase.auth.getUser();
  } catch (error) {
    // Log the error but don't fail the request
    console.warn("Supabase auth error:", error);
  }

  return supabaseResponse;
}

export async function middleware(request: NextRequest) {
  // Handle Supabase auth for all routes first
  const response = await updateSession(request);

  // Only apply rate limiting to chat API
  if (!request.nextUrl.pathname.startsWith("/api/chat")) {
    return response;
  }

  // Skip rate limiting for attachment uploads (different limits apply)
  if (request.nextUrl.pathname === "/api/chat/attachments") {
    return response;
  }

  // Get identifier (IP address or authenticated user)
  const ip =
    request.headers.get("x-forwarded-for")?.split(",")[0] ||
    request.headers.get("x-real-ip") ||
    "127.0.0.1";

  // Check for authenticated user (if auth token exists)
  const authHeader = request.headers.get("authorization");
  const identifier = authHeader ? `auth:${authHeader}` : `ip:${ip}`;

  // Apply rate limiting
  const rateLimitResult = rateLimiter.check(identifier);

  // Create rate limit response if needed
  const rateLimitResponse = rateLimitResult.success
    ? response
    : NextResponse.json(
        {
          error: "Too many requests. Please wait before trying again.",
          code: "RATE_LIMITED",
          retryAfter: Math.ceil((rateLimitResult.reset - Date.now()) / 1000),
        },
        { status: 429 }
      );

  // Add rate limit headers
  rateLimitResponse.headers.set("X-RateLimit-Limit", rateLimitResult.limit.toString());
  rateLimitResponse.headers.set(
    "X-RateLimit-Remaining",
    rateLimitResult.remaining.toString()
  );
  rateLimitResponse.headers.set(
    "X-RateLimit-Reset",
    Math.floor(rateLimitResult.reset / 1000).toString()
  );

  // Add retry-after header for 429 responses
  if (!rateLimitResult.success) {
    rateLimitResponse.headers.set(
      "Retry-After",
      Math.ceil((rateLimitResult.reset - Date.now()) / 1000).toString()
    );
  }

  return rateLimitResponse;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    "/((?!_next/static|_next/image|favicon.ico|public).*)",
  ],
};
