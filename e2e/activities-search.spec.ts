import { expect, test } from "@playwright/test";
import { authenticateAsTestUser, resetTestAuth } from "./helpers/auth";

test.describe("Activities Search", () => {
  test.beforeEach(async ({ page }) => {
    await resetTestAuth(page);
  });

  test("renders the authenticated activities search page", async ({ page }) => {
    await authenticateAsTestUser(page);
    await page.goto("/dashboard/search/activities", { waitUntil: "domcontentloaded" });

    await expect(page.getByRole("heading", { level: 1, name: "Search" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Search Activities" })
    ).toBeVisible();
    await expect(page.getByText("Discover Amazing Activities")).toBeVisible();
  });
});
