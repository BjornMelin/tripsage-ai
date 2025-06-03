import { type NextRequest, NextResponse } from "next/server";
import { jwtVerify } from "jose";

// Environment variables
const JWT_SECRET = new TextEncoder().encode(
  process.env.JWT_SECRET || "fallback-secret-for-development-only"
);

// Simple in-memory rate limiter
const rateLimitStore = new Map<string, { count: number; resetTime: number }>();

// Define protected routes that require authentication
const PROTECTED_ROUTES = [
  "/dashboard",
  "/chat",
  "/trips",
  "/profile",
  "/settings",
  "/search/flights",
  "/search/hotels",
  "/search/activities",
];

// Define public routes that should redirect authenticated users
const AUTH_ROUTES = ["/login", "/register", "/reset-password"];

// API routes that require authentication
const PROTECTED_API_ROUTES = [
  "/api/chat",
  "/api/trips",
  "/api/search",
  "/api/user",
  "/api/settings",
];

// Clean up old entries periodically
setInterval(() => {
  const now = Date.now();
  for (const [key, value] of rateLimitStore.entries()) {
    if (now > value.resetTime) {
      rateLimitStore.delete(key);
    }
  }
}, 60000); // Clean up every minute

function checkRateLimit(
  identifier: string,
  limit = 10,
  windowMs = 60000
): {
  success: boolean;
  limit: number;
  remaining: number;
  reset: number;
} {
  const now = Date.now();
  const record = rateLimitStore.get(identifier);
  const resetTime = now + windowMs;

  if (!record || now > record.resetTime) {
    // Create new record
    rateLimitStore.set(identifier, {
      count: 1,
      resetTime,
    });
    return {
      success: true,
      limit,
      remaining: limit - 1,
      reset: resetTime,
    };
  }

  if (record.count >= limit) {
    // Rate limit exceeded
    return {
      success: false,
      limit,
      remaining: 0,
      reset: record.resetTime,
    };
  }

  // Increment count
  record.count++;
  return {
    success: true,
    limit,
    remaining: limit - record.count,
    reset: record.resetTime,
  };
}

async function handleRateLimiting(request: NextRequest): Promise<NextResponse> {
  // Only apply rate limiting to chat API
  if (!request.nextUrl.pathname.startsWith("/api/chat")) {
    return NextResponse.next();
  }

  // Skip rate limiting for attachment uploads (different limits apply)
  if (request.nextUrl.pathname === "/api/chat/attachments") {
    return NextResponse.next();
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
  const rateLimitResult = checkRateLimit(identifier);

  // Create response
  const response = rateLimitResult.success
    ? NextResponse.next()
    : NextResponse.json(
        {
          error: "Too many requests. Please wait before trying again.",
          code: "RATE_LIMITED",
          retryAfter: Math.ceil((rateLimitResult.reset - Date.now()) / 1000),
        },
        { status: 429 }
      );

  // Add rate limit headers
  response.headers.set("X-RateLimit-Limit", rateLimitResult.limit.toString());
  response.headers.set("X-RateLimit-Remaining", rateLimitResult.remaining.toString());
  response.headers.set(
    "X-RateLimit-Reset",
    Math.floor(rateLimitResult.reset / 1000).toString()
  );

  // Add retry-after header for 429 responses
  if (!rateLimitResult.success) {
    response.headers.set(
      "Retry-After",
      Math.ceil((rateLimitResult.reset - Date.now()) / 1000).toString()
    );
  }

  return response;
}

/**
 * Verify JWT token from cookies
 */
async function verifyToken(token: string): Promise<boolean> {
  try {
    await jwtVerify(token, JWT_SECRET);
    return true;
  } catch (error) {
    return false;
  }
}

/**
 * Check if the pathname matches any of the patterns
 */
function matchesPattern(pathname: string, patterns: string[]): boolean {
  return patterns.some((pattern) => {
    // Exact match or starts with pattern (for nested routes)
    return pathname === pattern || pathname.startsWith(`${pattern}/`);
  });
}

async function handleAuthentication(
  request: NextRequest
): Promise<NextResponse | null> {
  const { pathname } = request.nextUrl;
  const authToken = request.cookies.get("auth-token");

  // Skip authentication for static files and public assets
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/static") ||
    pathname.includes(".") || // Files with extensions
    pathname === "/" // Home page is public
  ) {
    return null;
  }

  // Verify authentication status
  const isAuthenticated = authToken ? await verifyToken(authToken.value) : false;

  // Handle protected routes
  if (matchesPattern(pathname, PROTECTED_ROUTES)) {
    if (!isAuthenticated) {
      // Redirect to login with return URL
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("from", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // Handle auth routes (login, register, reset-password)
  if (matchesPattern(pathname, AUTH_ROUTES)) {
    if (isAuthenticated) {
      // Redirect authenticated users away from auth pages
      const returnUrl = request.nextUrl.searchParams.get("from") || "/dashboard";
      return NextResponse.redirect(new URL(returnUrl, request.url));
    }
  }

  // Handle protected API routes
  if (matchesPattern(pathname, PROTECTED_API_ROUTES)) {
    if (!isAuthenticated) {
      // Return 401 for unauthenticated API requests
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }
  }

  // Add authentication status to request headers for server components
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-is-authenticated", isAuthenticated ? "true" : "false");

  return null;
}

export async function middleware(request: NextRequest) {
  // First, handle authentication
  const authResponse = await handleAuthentication(request);
  if (authResponse) {
    return authResponse;
  }

  // Then apply rate limiting
  return handleRateLimiting(request);
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
