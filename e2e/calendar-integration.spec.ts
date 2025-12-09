import { expect, test } from "@playwright/test";

test.describe("Calendar Integration", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to calendar page with timeout
    await page.goto("/dashboard/calendar", { waitUntil: "domcontentloaded" });
  });

  test("calendar page loads and shows connection status", async ({ page }) => {
    // Verify page title
    await expect(page.getByRole("heading", { name: /calendar/i })).toBeVisible({
      timeout: 5000,
    });

    // Verify tabs are present (parallel checks)
    await Promise.all([
      expect(page.getByRole("tab", { name: /connection/i })).toBeVisible(),
      expect(page.getByRole("tab", { name: /events/i })).toBeVisible(),
      expect(page.getByRole("tab", { name: /create/i })).toBeVisible(),
    ]);

    // Verify connection status section is visible
    await expect(
      page
        .getByText(/connect your google calendar/i)
        .or(page.getByText(/calendar connected/i))
    ).toBeVisible({ timeout: 5000 });
  });

  test("calendar event form renders correctly", async ({ page }) => {
    // Navigate to create event tab
    await page.getByRole("tab", { name: /create/i }).click();

    // Verify form fields are present (parallel checks for speed)
    await Promise.all([
      expect(page.getByLabel(/title|summary/i)).toBeVisible(),
      expect(page.getByLabel(/description/i)).toBeVisible(),
      expect(page.getByLabel(/location/i)).toBeVisible(),
      expect(page.getByLabel(/start/i)).toBeVisible(),
      expect(page.getByLabel(/end/i)).toBeVisible(),
    ]);

    // Verify submit button
    await expect(page.getByRole("button", { name: /create event/i })).toBeVisible();
  });

  test("calendar events list renders", async ({ page }) => {
    // Navigate to events tab
    await page.getByRole("tab", { name: /events/i }).click();

    // Verify events section is visible (may be empty)
    await expect(
      page.getByText(/upcoming events/i).or(page.getByText(/no upcoming events/i))
    ).toBeVisible();
  });

  test("calendar navigation link exists in sidebar", async ({ page }) => {
    // Navigate to dashboard first
    await page.goto("/dashboard");

    // Verify calendar link in navigation
    await expect(page.getByRole("link", { name: /calendar/i })).toBeVisible();

    // Click calendar link
    await page.getByRole("link", { name: /calendar/i }).click();

    // Verify we're on calendar page
    await expect(page).toHaveURL(/\/dashboard\/calendar/);
  });
});

test.describe("Calendar Export from Trip", () => {
  test("trip detail page has export to calendar button", async ({ page }) => {
    // Navigate to a trip detail page (assuming trips exist)
    await page.goto("/dashboard/trips", { waitUntil: "domcontentloaded" });

    // Check if trips are listed with timeout
    const tripLinks = page.getByRole("link", { name: /trip/i });
    const count = await tripLinks.count().catch(() => 0);

    if (count > 0) {
      // Click first trip
      await tripLinks.first().click();
      await page.waitForLoadState("domcontentloaded");

      // Verify export button exists
      await expect(
        page.getByRole("button", { name: /export to calendar/i })
      ).toBeVisible({ timeout: 5000 });
    } else {
      // Skip test if no trips exist (common in test environments)
      test.skip();
    }
  });
});
