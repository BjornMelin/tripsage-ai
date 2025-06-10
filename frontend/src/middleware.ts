import { type NextRequest, NextResponse } from "next/server";
import { jwtVerify } from "jose";

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

// JWT verification helper
async function verifyJwtToken(token: string): Promise<boolean> {
  try {
    const jwtSecret = process.env.JWT_SECRET;
    if (!jwtSecret) {
      console.warn("JWT_SECRET environment variable is not set");
      return false;
    }

    const secret = new TextEncoder().encode(jwtSecret);
    await jwtVerify(token, secret);
    return true;
  } catch (error) {
    console.warn("JWT verification failed:", error);
    return false;
  }
}

// Protected routes configuration
const protectedRoutes = [
  "/dashboard",
  "/chat",
  "/trips",
  "/profile",
  "/search",
  "/settings",
];

const authRoutes = ["/login", "/register", "/reset-password"];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const response = NextResponse.next();

  // Handle authentication for protected routes
  if (protectedRoutes.some(route => pathname.startsWith(route))) {
    // Check for JWT token in Authorization header or cookie
    const authHeader = request.headers.get("authorization");
    const token = authHeader?.replace("Bearer ", "") || 
                  request.cookies.get("auth-token")?.value;

    if (!token || !(await verifyJwtToken(token))) {
      // Redirect to login if not authenticated
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("redirectTo", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // Redirect authenticated users away from auth pages
  if (authRoutes.some(route => pathname.startsWith(route))) {
    const authHeader = request.headers.get("authorization");
    const token = authHeader?.replace("Bearer ", "") || 
                  request.cookies.get("auth-token")?.value;

    if (token && (await verifyJwtToken(token))) {
      const redirectTo = request.nextUrl.searchParams.get("redirectTo") || "/dashboard";
      return NextResponse.redirect(new URL(redirectTo, request.url));
    }
  }

  // Only apply rate limiting to chat API
  if (!pathname.startsWith("/api/chat")) {
    return response;
  }

  // Skip rate limiting for attachment uploads (different limits apply)
  if (pathname === "/api/chat/attachments") {
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
