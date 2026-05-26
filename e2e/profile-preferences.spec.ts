import { expect, test } from "@playwright/test";
import { authenticateAsTestUser, resetTestAuth } from "./helpers/auth";

const visibilityTimeoutMs = 15_000;

test.describe("Profile preferences", () => {
  test.beforeEach(async ({ page }) => {
    await resetTestAuth(page);
  });

  test("renders the preferences section for an authenticated user", async ({
    page,
  }) => {
    await authenticateAsTestUser(page);
    await page.goto("/dashboard/profile", { waitUntil: "domcontentloaded" });

    await expect(
      page.getByRole("heading", { exact: true, name: "Profile" })
    ).toBeVisible({ timeout: visibilityTimeoutMs });

    const avatarUpload = page.getByRole("button", {
      exact: true,
      name: "Upload profile picture",
    });
    await expect(avatarUpload).toBeVisible({ timeout: visibilityTimeoutMs });
    await expect(avatarUpload).toHaveAccessibleDescription(
      /recommended size: 400x400px/i
    );

    await page.getByRole("tab", { name: /Preferences/i }).click();

    await expect(page.getByText("Regional & Language")).toBeVisible({
      timeout: visibilityTimeoutMs,
    });
    await expect(page.getByText("Additional Settings")).toBeVisible({
      timeout: visibilityTimeoutMs,
    });
  });

  test("renders named account notification switches", async ({ page }) => {
    await authenticateAsTestUser(page);
    await page.goto("/dashboard/profile", { waitUntil: "domcontentloaded" });

    await expect(
      page.getByRole("heading", { exact: true, name: "Profile" })
    ).toBeVisible({ timeout: visibilityTimeoutMs });

    await page.getByRole("tab", { name: /Account/i }).click();

    await expect(
      page.getByRole("switch", { name: "Email Notifications" })
    ).toHaveAccessibleDescription(
      "Receive trip updates and important account information via email."
    );
    await expect(
      page.getByRole("switch", { name: "Trip Reminders" })
    ).toHaveAccessibleDescription("Get reminders about upcoming trips and bookings.");
    await expect(
      page.getByRole("switch", { name: "Price Alerts" })
    ).toHaveAccessibleDescription(
      "Receive notifications when flight or hotel prices drop."
    );
    await expect(
      page.getByRole("switch", { name: "Marketing Communications" })
    ).toHaveAccessibleDescription("Receive promotional offers and travel tips.");
  });

  test("renders named preference setting switches", async ({ page }) => {
    await authenticateAsTestUser(page);
    await page.goto("/dashboard/profile", { waitUntil: "domcontentloaded" });

    await expect(
      page.getByRole("heading", { exact: true, name: "Profile" })
    ).toBeVisible({ timeout: visibilityTimeoutMs });

    await page.getByRole("tab", { name: /Preferences/i }).click();

    await expect(
      page.getByRole("switch", { name: "Auto-save Searches" })
    ).toHaveAccessibleDescription(
      "Automatically save your search history for quick access."
    );
    await expect(
      page.getByRole("switch", { name: "Smart Suggestions" })
    ).toHaveAccessibleDescription(
      "Get AI-powered travel suggestions based on your preferences."
    );
    await expect(
      page.getByRole("switch", { name: "Location Services" })
    ).toHaveAccessibleDescription("Allow location access for nearby recommendations.");
    await expect(
      page.getByRole("switch", { name: "Analytics" })
    ).toHaveAccessibleDescription("Help us improve by sharing anonymous usage data.");
  });
});
