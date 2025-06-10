import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Request validation schema
const RefreshRequestSchema = z.object({
  refreshToken: z.string().min(1, "Refresh token is required"),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate request body
    const validatedData = RefreshRequestSchema.parse(body);

    // Make request to FastAPI backend
    const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        refresh_token: validatedData.refreshToken,
      }),
    });

    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => ({ message: "Token refresh failed" }));
      return NextResponse.json(
        { error: errorData.message || "Token refresh failed" },
        { status: response.status }
      );
    }

    const tokenData = await response.json();

    // Transform backend response to frontend format
    const responseData = {
      accessToken: tokenData.access_token,
      refreshToken: tokenData.refresh_token || validatedData.refreshToken, // Keep old refresh token if not provided
      expiresAt: new Date(Date.now() + tokenData.expires_in * 1000).toISOString(),
      tokenType: tokenData.token_type || "Bearer",
    };

    return NextResponse.json(responseData);
  } catch (error) {
    console.error("Token refresh API error:", error);

    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: "Invalid request data", details: error.errors },
        { status: 400 }
      );
    }

    return NextResponse.json({ error: "Token refresh failed" }, { status: 401 });
  }
}
