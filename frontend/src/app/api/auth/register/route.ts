import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Request validation schema
const RegisterRequestSchema = z
  .object({
    email: z.string().email("Invalid email format"),
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirmPassword: z.string().min(1, "Password confirmation is required"),
    firstName: z.string().optional(),
    lastName: z.string().optional(),
    acceptTerms: z
      .boolean()
      .refine((val) => val === true, "You must accept the terms and conditions"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate request body
    const validatedData = RegisterRequestSchema.parse(body);

    // Make request to FastAPI backend
    const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: validatedData.email,
        password: validatedData.password,
        first_name: validatedData.firstName,
        last_name: validatedData.lastName,
        accept_terms: validatedData.acceptTerms,
      }),
    });

    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => ({ message: "Registration failed" }));
      return NextResponse.json(
        { error: errorData.message || "Registration failed" },
        { status: response.status }
      );
    }

    const authData = await response.json();

    // Transform backend response to frontend format
    const responseData = {
      user: {
        id: authData.user?.id,
        email: authData.user?.email,
        displayName: authData.user?.display_name || authData.user?.email?.split("@")[0],
        firstName: authData.user?.first_name,
        lastName: authData.user?.last_name,
        avatarUrl: authData.user?.avatar_url,
        isEmailVerified: authData.user?.is_email_verified || false,
        bio: authData.user?.bio,
        location: authData.user?.location,
        website: authData.user?.website,
        preferences: authData.user?.preferences,
        security: authData.user?.security,
        createdAt: authData.user?.created_at,
        updatedAt: authData.user?.updated_at,
      },
      tokenInfo: {
        accessToken: authData.access_token,
        refreshToken: authData.refresh_token,
        expiresAt: new Date(Date.now() + authData.expires_in * 1000).toISOString(),
        tokenType: authData.token_type || "Bearer",
      },
      session: {
        id: authData.session_id || `session_${Date.now()}`,
        userId: authData.user?.id,
        deviceInfo: {
          userAgent: request.headers.get("user-agent") || undefined,
          ipAddress:
            request.headers.get("x-forwarded-for") ||
            request.headers.get("x-real-ip") ||
            undefined,
        },
        createdAt: new Date().toISOString(),
        lastActivity: new Date().toISOString(),
        expiresAt: new Date(Date.now() + authData.expires_in * 1000).toISOString(),
      },
    };

    return NextResponse.json(responseData);
  } catch (error) {
    console.error("Register API error:", error);

    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: "Invalid request data", details: error.errors },
        { status: 400 }
      );
    }

    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
