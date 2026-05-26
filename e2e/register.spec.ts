import { expect, test } from "@playwright/test";
import { resetTestAuth } from "./helpers/auth";

test.describe("Registration", () => {
  test.beforeEach(async ({ page }) => {
    await resetTestAuth(page);
  });

  test("renders the unauthenticated registration page", async ({ page }) => {
    await page.goto("/register", { waitUntil: "domcontentloaded" });

    await expect(page.getByRole("heading", { name: /create account/i })).toBeVisible();

    for (const fieldName of [
      "First name",
      "Last name",
      "Email",
      "Password",
      "Confirm password",
    ]) {
      await expect(
        page.getByLabel(fieldName, { exact: true })
      ).toHaveAccessibleDescription("Join TripSage to start planning");
    }

    await expect(page.getByRole("button", { name: /create account/i })).toBeVisible();
    await expect(
      page.getByRole("button", { name: /continue with github/i })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /continue with google/i })
    ).toBeVisible();
  });
});
