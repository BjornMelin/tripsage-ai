import { expect, test } from "@playwright/test";
import { authenticateAsTestUser, resetTestAuth } from "./helpers/auth";

test.describe("Loading States", () => {
  test.beforeEach(async ({ page }) => {
    await resetTestAuth(page);
    await authenticateAsTestUser(page);
  });

  test("dashboard shows skeletons while metrics load", async ({ page }) => {
    await page.route("**/api/dashboard**", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 800));
      await route.fulfill({
        body: JSON.stringify({
          activeTrips: 0,
          avgLatencyMs: 123.4,
          completedTrips: 0,
          errorRate: 0,
          totalRequests: 42,
          totalTrips: 0,
        }),
        contentType: "application/json",
        status: 200,
      });
    });

    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });

    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible({
      timeout: 15000,
    });

    // Dashboard metrics uses client-side Skeleton components (role="status").
    const skeleton = page
      .locator('[role="status"][aria-label="Loading content..."]')
      .first();
    await expect(skeleton).toBeVisible({ timeout: 15000 });

    // Eventually the metrics section renders after the API responds.
    await expect(page.getByRole("heading", { name: "System Metrics" })).toBeVisible({
      timeout: 15000,
    });
  });

  test("skeletons expose aria labels for accessibility", async ({ page }) => {
    await page.route("**/api/dashboard**", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 800));
      await route.fulfill({
        body: JSON.stringify({
          activeTrips: 0,
          avgLatencyMs: 0,
          completedTrips: 0,
          errorRate: 0,
          totalRequests: 0,
          totalTrips: 0,
        }),
        contentType: "application/json",
        status: 200,
      });
    });

    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });

    const skeleton = page
      .locator('[role="status"][aria-label="Loading content..."]')
      .first();
    await expect(skeleton).toBeVisible({ timeout: 15000 });
  });
});
