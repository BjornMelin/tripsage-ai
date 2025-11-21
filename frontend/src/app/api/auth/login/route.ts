/**
 * @fileoverview Login API route.
 *
 * Handles email/password login authentication using Supabase SSR.
 * Includes validation, authentication, and returns appropriate responses.
 */

import "server-only";

import { loginFormSchema } from "@schemas/auth";
import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";
import { recordTelemetryEvent } from "@/lib/telemetry/span";

/**
 * POST /api/auth/login
 *
 * Authenticates a user with email and password.
 * Returns success/error status without redirects (client handles navigation).
 */
export async function POST(request: Request) {
  try {
    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        {
          error: "Invalid JSON payload",
          success: false,
        },
        { status: 400 }
      );
    }
    const parsed = loginFormSchema.safeParse(body);

    if (!parsed.success) {
      // Map Zod validation errors to field-specific messages
      const fieldErrors: Record<string, string> = {};
      for (const issue of parsed.error.issues) {
        const field = issue.path[0];
        if (field === "email") {
          fieldErrors.email = issue.message;
        } else if (field === "password") {
          fieldErrors.password = issue.message;
        }
      }

      return NextResponse.json(
        {
          error: "Please check your input and try again",
          fieldErrors,
          success: false,
        },
        { status: 400 }
      );
    }

    const supabase = await createServerSupabase();
    const { error } = await supabase.auth.signInWithPassword({
      email: parsed.data.email,
      password: parsed.data.password,
    });

    if (error) {
      recordTelemetryEvent("auth.login.failure", {
        attributes: {
          reason: error.message || "unknown_error",
        },
        level: "error",
      });
      return NextResponse.json(
        {
          error: error.message || "Login failed",
          success: false,
        },
        { status: 401 }
      );
    }

    // Success: return success status
    recordTelemetryEvent("auth.login.success", { level: "info" });
    return NextResponse.json({
      success: true,
    });
  } catch (error) {
    recordTelemetryEvent("auth.login.error", {
      attributes: {
        message: error instanceof Error ? error.message : "unknown_error",
      },
      level: "error",
    });
    return NextResponse.json(
      {
        error: "An unexpected error occurred",
        success: false,
      },
      { status: 500 }
    );
  }
}
