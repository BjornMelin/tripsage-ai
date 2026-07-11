import { expect, test } from "@playwright/test";
import { resetTestAuth } from "./helpers/auth";

test.describe("Password reset", () => {
  test.beforeEach(async ({ page }) => {
    await resetTestAuth(page);
  });

  test("renders the unauthenticated password reset request page", async ({ page }) => {
    await page.goto("/reset-password", { waitUntil: "domcontentloaded" });

    await expect(
      page.getByRole("heading", { name: /reset your password/i })
    ).toBeVisible();
    const emailInput = page.getByLabel("Email Address");
    await expect(emailInput).toBeVisible();
    await expect(emailInput).toHaveAccessibleDescription(
      /we'll send password reset instructions/i
    );
    await expect(
      page.getByRole("button", { name: /send reset instructions/i })
    ).toBeVisible();
    await expect(page.getByRole("link", { name: /back to sign in/i })).toHaveAttribute(
      "href",
      "/login"
    );
  });

  test("announces successful reset request feedback as status", async ({ page }) => {
    let resetRequestCount = 0;
    await page.route("**/auth/password/reset-request**", async (route) => {
      resetRequestCount += 1;
      await route.fulfill({
        body: JSON.stringify({
          message: "Password reset instructions have been sent to your email",
        }),
        headers: { "Content-Type": "application/json" },
        status: 200,
      });
    });

    await page.goto("/reset-password", { waitUntil: "networkidle" });
    const emailInput = page.getByLabel("Email Address");
    await expect(emailInput).toBeEditable();
    await emailInput.fill("traveler@example.com");
    await expect(emailInput).toHaveValue("traveler@example.com");

    const submit = page.getByRole("button", { name: /send reset instructions/i });
    const success = page.getByRole("status").filter({
      hasText: /password reset instructions have been sent to your email/i,
    });
    await submit.click();
    await expect(success).toBeVisible({ timeout: 15_000 });
    expect(resetRequestCount).toBe(1);
  });
});
