import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  try {
    // Get authorization header
    const authHeader = request.headers.get("authorization");

    if (!authHeader || !authHeader.startsWith("Bearer ")) {
      return NextResponse.json(
        { error: "No valid authorization token provided" },
        { status: 401 }
      );
    }

    // Make request to FastAPI backend
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      method: "GET",
      headers: {
        Authorization: authHeader,
      },
    });

    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => ({ message: "Failed to get user info" }));
      return NextResponse.json(
        { error: errorData.message || "Authentication failed" },
        { status: response.status }
      );
    }

    const userData = await response.json();

    // Transform backend response to frontend format
    const responseData = {
      id: userData.id,
      email: userData.email,
      displayName: userData.display_name || userData.email?.split("@")[0],
      firstName: userData.first_name,
      lastName: userData.last_name,
      avatarUrl: userData.avatar_url,
      isEmailVerified: userData.is_email_verified || false,
      bio: userData.bio,
      location: userData.location,
      website: userData.website,
      preferences: userData.preferences,
      security: userData.security,
      createdAt: userData.created_at,
      updatedAt: userData.updated_at,
    };

    return NextResponse.json(responseData);
  } catch (error) {
    console.error("Get user API error:", error);

    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
