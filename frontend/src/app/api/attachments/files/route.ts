/**
 * @fileoverview API route for fetching attachment files with pagination support.
 * Provides a proxy endpoint to the backend API for retrieving user attachment files.
 */

"use cache: private";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://localhost:8001";

/**
 * Retrieves attachment files with optional pagination parameters.
 *
 * @param req - The Next.js request object containing query parameters.
 * @returns A JSON response with attachment files data or an error response.
 * @throws Will return a 500 status response for internal server errors.
 */
export async function GET(req: NextRequest) {
  try {
    // Forward Authorization when present
    const authHeader = req.headers.get("authorization");

    // Preserve pagination query params
    const { searchParams } = req.nextUrl;
    const qs = searchParams.toString();
    const url = `${BACKEND_API_URL}/api/attachments/files${qs ? `?${qs}` : ""}`;

    const response = await fetch(url, {
      headers: authHeader ? { Authorization: authHeader } : undefined,
      method: "GET",
      // Tag reads so uploads can revalidate via revalidateTag('attachments', 'max')
      next: { tags: ["attachments"] },
    });

    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json(
        { error: data?.detail || "Failed to fetch attachments" },
        { status: response.status }
      );
    }

    return NextResponse.json(data, { status: 200 });
  } catch (_error) {
    return NextResponse.json(
      { code: "INTERNAL_ERROR", error: "Internal server error" },
      { status: 500 }
    );
  }
}
