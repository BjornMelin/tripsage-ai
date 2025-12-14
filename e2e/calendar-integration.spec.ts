import { expect, test } from "@playwright/test";
import { authenticateAsTestUser, resetTestAuth } from "./helpers/auth";

test.describe("Calendar Integration", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to calendar page with timeout
    await resetTestAuth(page);
    await authenticateAsTestUser(page);
    await page.route("**/api/calendar/status", async (route) => {
      await route.fulfill({
        body: JSON.stringify({ connected: false }),
        contentType: "application/json",
        status: 200,
      });
    });

    await page.route("**/api/calendar/events**", async (route) => {
      await route.fulfill({
        body: JSON.stringify({ items: [] }),
        contentType: "application/json",
        status: 200,
      });
    });
    await page.goto("/dashboard/calendar", { waitUntil: "load" });
    await expect(page.getByText("Calendar Not Connected")).toBeVisible({
      timeout: 15000,
    });
  });

  test("calendar page loads and shows connection status", async ({ page }) => {
    // Verify page title
    await expect(page.getByRole("heading", { level: 2, name: "Calendar" })).toBeVisible(
      {
        timeout: 5000,
      }
    );

    // Verify tabs are present (parallel checks)
    await Promise.all([
      expect(page.getByRole("tab", { name: /connection/i })).toBeVisible(),
      expect(page.getByRole("tab", { name: /events/i })).toBeVisible(),
      expect(page.getByRole("tab", { name: /create/i })).toBeVisible(),
    ]);

    // Verify connection status section is visible
    await expect(page.getByText("Calendar Not Connected")).toBeVisible({
      timeout: 5000,
    });
  });

  test("calendar event form renders correctly", async ({ page }) => {
    // Navigate to create event tab
    const createTab = page.getByRole("tab", { name: "Create Event" });
    await createTab.click();
    await expect(createTab).toHaveAttribute("aria-selected", "true");
    await expect(page.getByText("Create Calendar Event")).toBeVisible({
      timeout: 15000,
    });

    // Verify form fields are present (parallel checks for speed)
    await Promise.all([
      expect(page.getByLabel("Title")).toBeVisible(),
      expect(page.getByLabel("Description")).toBeVisible(),
      expect(page.getByLabel("Location")).toBeVisible(),
      expect(page.getByLabel("Start")).toBeVisible(),
      expect(page.getByLabel("End")).toBeVisible(),
    ]);

    // Verify submit button
    await expect(page.getByRole("button", { name: /create event/i })).toBeVisible();
  });

  test("calendar events list renders", async ({ page }) => {
    // Navigate to events tab
    const eventsTab = page.getByRole("tab", { name: "Events" });
    await eventsTab.click();
    await expect(eventsTab).toHaveAttribute("aria-selected", "true");
    await expect(page.getByRole("heading", { name: "Upcoming Events" })).toBeVisible({
      timeout: 15000,
    });

    // Verify events section is visible (may be empty)
    await expect(page.getByText("No upcoming events")).toBeVisible({ timeout: 15000 });
  });

  test("calendar navigation link exists in sidebar", async ({ page }) => {
    // Dashboard layout sidebar should expose a Calendar link
    await expect(page.getByRole("link", { name: /calendar/i })).toBeVisible();
  });
});

test.describe("Calendar Export from Trip", () => {
  test("trip detail page has export to calendar button", async ({ page }) => {
    // Navigate to a trip detail page (assuming trips exist)
    await resetTestAuth(page);
    await authenticateAsTestUser(page);
    await page.goto("/dashboard/trips", { waitUntil: "load" });

    // Check if trips are listed with timeout
    const detailLinks = page.getByRole("link", { name: "View Details" });
    const count = await detailLinks.count();

    if (count > 0) {
      // Click first trip
      await detailLinks.first().click();
      await page.waitForLoadState("load");

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
