import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
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
    const response = await fetch(`${API_BASE_URL}/api/auth/logout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": authHeader,
      },
    });

    if (!response.ok) {
      // Even if backend logout fails, we'll return success
      // since the client will clear its local state anyway
      console.warn("Backend logout failed:", response.status);
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Logout API error:", error);
    
    // Return success anyway since logout should always succeed on client
    return NextResponse.json({ success: true });
  }
}