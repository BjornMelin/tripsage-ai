/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { authRouteErrorResponse } from "../route-error-response";

describe("authRouteErrorResponse", () => {
  it("returns standardized errors with legacy auth fields", async () => {
    const response = authRouteErrorResponse({
      code: "RESET_FAILED",
      reason: "Password reset failed",
      status: 400,
    });

    expect(response.status).toBe(400);
    await expect(response.json()).resolves.toEqual({
      code: "RESET_FAILED",
      error: "reset_failed",
      message: "Password reset failed",
      reason: "Password reset failed",
    });
  });

  it("uses explicit error codes when no legacy code is provided", async () => {
    const response = authRouteErrorResponse({
      error: "logout_failed",
      reason: "signout failed",
      status: 500,
    });

    expect(response.status).toBe(500);
    await expect(response.json()).resolves.toEqual({
      error: "logout_failed",
      message: "signout failed",
      reason: "signout failed",
    });
  });

  it("preserves extras without allowing them to override compatibility fields", async () => {
    const response = authRouteErrorResponse({
      code: "VALIDATION_ERROR",
      error: "invalid_auth_request",
      extras: {
        code: "OTHER_CODE",
        errors: [{ field: "email", message: "Invalid email" }],
        message: "Other message",
      },
      reason: "Invalid auth request",
      status: 400,
    });

    expect(response.status).toBe(400);
    await expect(response.json()).resolves.toEqual({
      code: "VALIDATION_ERROR",
      error: "invalid_auth_request",
      errors: [{ field: "email", message: "Invalid email" }],
      message: "Invalid auth request",
      reason: "Invalid auth request",
    });
  });
});
