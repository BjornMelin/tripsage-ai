import { expect, test } from "@playwright/test";
import { resetTestAuth } from "./helpers/auth";

test.describe("Auth route feedback", () => {
  test.beforeEach(async ({ page }) => {
    await resetTestAuth(page);
  });

  test("announces login query-parameter errors", async ({ page }) => {
    await page.goto("/login?error=auth_confirm_failed&error_code=otp_expired", {
      waitUntil: "domcontentloaded",
    });

    await expect(
      page.getByRole("alert").filter({ hasText: /this email link has expired/i })
    ).toBeVisible();
  });

  test("announces register check-email and error feedback", async ({ page }) => {
    await page.goto("/register?status=check_email", {
      waitUntil: "domcontentloaded",
    });

    await expect(
      page
        .getByRole("status")
        .filter({ hasText: /check your email to confirm your account/i })
    ).toBeVisible();

    await page.goto("/register?error=email_taken", {
      waitUntil: "domcontentloaded",
    });

    await expect(
      page.getByRole("alert").filter({ hasText: /this email is already registered/i })
    ).toBeVisible();
  });
});
