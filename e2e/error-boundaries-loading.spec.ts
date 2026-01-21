import { expect, type Page, test } from "@playwright/test";
import { authenticateAsTestUser, resetTestAuth } from "./helpers/auth";

type DashboardApiBody = {
  activeTrips: number;
  avgLatencyMs: number;
  completedTrips: number;
  errorRate: number;
  totalRequests: number;
  totalTrips: number;
};

const defaultDashboardApiBody: DashboardApiBody = {
  activeTrips: 0,
  avgLatencyMs: 0,
  completedTrips: 0,
  errorRate: 0,
  totalRequests: 0,
  totalTrips: 0,
};

async function mockDashboardApi(
  page: Page,
  options: {
    delayMs?: number;
    bodyOverrides?: Partial<DashboardApiBody>;
  } = {}
): Promise<void> {
  const { delayMs = 800, bodyOverrides } = options;

  await page.route("**/api/dashboard**", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    await route.fulfill({
      body: JSON.stringify({ ...defaultDashboardApiBody, ...bodyOverrides }),
      contentType: "application/json",
      status: 200,
    });
  });
}

test.describe("Loading States", () => {
  test.beforeEach(async ({ page }) => {
    await resetTestAuth(page);
    await authenticateAsTestUser(page);
  });

  test("dashboard shows skeletons while metrics load", async ({ page }) => {
    await mockDashboardApi(page, {
      bodyOverrides: { avgLatencyMs: 123.4, totalRequests: 42 },
    });

    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });

    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible({
      timeout: 15000,
    });

    // Dashboard metrics uses client-side Skeleton components (role="status").
    const skeleton = page
      .locator('[role="status"][aria-label="Loading content…"]')
      .first();
    await expect(skeleton).toBeVisible({ timeout: 15000 });

    // Eventually the metrics section renders after the API responds.
    await expect(page.getByRole("heading", { name: "System Metrics" })).toBeVisible({
      timeout: 15000,
    });
  });

  test("skeletons expose aria labels for accessibility", async ({ page }) => {
    await mockDashboardApi(page);

    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });

    const skeleton = page
      .locator('[role="status"][aria-label="Loading content…"]')
      .first();
    await expect(skeleton).toBeVisible({ timeout: 15000 });
  });
});
