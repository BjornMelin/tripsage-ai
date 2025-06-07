import { type NextRequest, NextResponse } from "next/server";

// Simple in-memory rate limiter
const rateLimitStore = new Map<string, { count: number; resetTime: number }>();

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

export async function middleware(request: NextRequest) {
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
