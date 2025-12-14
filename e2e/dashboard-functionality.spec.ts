import { expect, type Locator, type Page, test } from "@playwright/test";
import { authenticateAsTestUser, resetTestAuth } from "./helpers/auth";

const navigationTimeoutMs = 15_000;

async function clickAndWaitForUrl(
  page: Page,
  locator: Locator,
  url: string,
  options: { attempts?: number; timeoutMs?: number } = {}
): Promise<void> {
  const attempts = options.attempts ?? 2;
  const timeoutMs = options.timeoutMs ?? navigationTimeoutMs;

  for (let attempt = 0; attempt < attempts; attempt++) {
    await locator.click();
    try {
      await expect(page).toHaveURL(url, { timeout: timeoutMs });
      return;
    } catch (error) {
      if (attempt === attempts - 1) {
        throw error;
      }
    }
  }
}

test.describe("Dashboard Functionality", () => {
  test.beforeEach(async ({ page }) => {
    await resetTestAuth(page);
    // Navigate to the application
    await page.goto("/");
  });

  test("dashboard page renders correctly after authentication", async ({ page }) => {
    // Navigate to login page
    await page.goto("/login");

    // Verify login page loads
    await expect(page).toHaveTitle(/TripSage/);
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();

    await authenticateAsTestUser(page);
    await page.goto("/dashboard");

    // Verify dashboard content
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByText("Welcome to TripSage AI")).toBeVisible();

    // Verify quick actions are present
    await expect(page.getByText("Search Flights").first()).toBeVisible();
    await expect(page.getByText("Find Hotels")).toBeVisible();
    await expect(page.getByText("Ask AI Assistant")).toBeVisible();

    // Verify navigation elements (use more specific selectors)
    await expect(page.getByRole("navigation").getByText("Overview")).toBeVisible();
    await expect(page.getByRole("navigation").getByText("My Trips")).toBeVisible();
    await expect(page.getByRole("navigation").getByText("Search")).toBeVisible();
  });

  test("dashboard navigation works correctly", async ({ page }) => {
    await authenticateAsTestUser(page);
    await page.goto("/dashboard");

    // Test sidebar navigation
    await page.getByRole("navigation").getByRole("link", { name: "My Trips" }).click();
    await expect(page).toHaveURL("/dashboard/trips", { timeout: navigationTimeoutMs });

    await page.getByRole("navigation").getByRole("link", { name: "Search" }).click();
    await expect(page).toHaveURL("/dashboard/search", { timeout: navigationTimeoutMs });

    await page
      .getByRole("navigation")
      .getByRole("link", { name: "AI Assistant" })
      .click();
    await expect(page).toHaveURL("/chat", { timeout: navigationTimeoutMs });

    // Return to dashboard home from /chat
    await page.goto("/dashboard");
    await expect(page).toHaveURL("/dashboard", { timeout: navigationTimeoutMs });
  });

  test("user navigation menu works", async ({ page }) => {
    await authenticateAsTestUser(page);
    await page.goto("/dashboard");

    // Click on user menu
    await page.getByRole("button", { name: "User" }).click();

    // Wait for popover to be visible and target menu items within the popover content
    const popoverContent = page.locator("[data-radix-popper-content-wrapper]");
    await expect(popoverContent).toBeVisible({ timeout: 15000 });

    // Verify menu options using the popover container to avoid sidebar conflicts
    await expect(popoverContent.getByRole("link", { name: "Profile" })).toBeVisible({
      timeout: 15000,
    });
    await expect(popoverContent.getByRole("link", { name: "Settings" })).toBeVisible({
      timeout: 15000,
    });
    await expect(popoverContent.getByRole("button", { name: "Log out" })).toBeVisible({
      timeout: 15000,
    });

    // Test profile navigation
    await popoverContent.getByRole("link", { name: "Profile" }).click();
    await expect(page).toHaveURL("/dashboard/profile", {
      timeout: navigationTimeoutMs,
    });

    // Navigate back and test settings
    await page.goto("/dashboard");
    await page.getByRole("button", { name: "User" }).click();

    // Wait for popover again and click settings
    await expect(popoverContent).toBeVisible({ timeout: 15000 });
    await popoverContent.getByRole("link", { name: "Settings" }).click();
    await expect(page).toHaveURL("/dashboard/settings", {
      timeout: navigationTimeoutMs,
    });
  });

  test("logout functionality works", async ({ page }) => {
    await authenticateAsTestUser(page);
    await page.goto("/dashboard");

    // Click on user menu and logout
    await page.getByRole("button", { name: "User" }).click();

    // Wait for popover to be visible and target logout button within it
    const popoverContent = page.locator("[data-radix-popper-content-wrapper]");
    await expect(popoverContent).toBeVisible({ timeout: 15000 });
    await popoverContent.getByRole("button", { name: "Log out" }).click();

    // Wait for redirect to login page
    await page.waitForURL(/\/login/, { timeout: 15000 });
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible({
      timeout: 15000,
    });

    // Verify that trying to access dashboard redirects to login
    await page.goto("/dashboard");
    await page.waitForURL(/\/login/, { timeout: 15000 });
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible({
      timeout: 15000,
    });
  });

  test("theme toggle works", async ({ page }) => {
    await authenticateAsTestUser(page);
    await page.goto("/dashboard");

    // Target theme toggle specifically in the header banner to avoid duplicates
    const headerThemeToggle = page
      .getByRole("banner")
      .getByRole("button", { name: "Toggle theme" });
    await headerThemeToggle.click();

    // Verify theme menu options
    await expect(page.getByRole("menuitem", { name: "Light" })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "Dark" })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "System" })).toBeVisible();

    // Test theme switching
    await page.getByRole("menuitem", { name: "Dark" }).click();
    await expect(page.locator("html")).toHaveClass(/dark/);

    // Switch back to light
    await headerThemeToggle.click();
    await page.getByRole("menuitem", { name: "Light" }).click();
    await expect(page.locator("html")).not.toHaveClass(/dark/);
  });

  test("dashboard quick actions work", async ({ page }) => {
    await authenticateAsTestUser(page);
    await page.goto("/dashboard");

    // Test quick action navigation
    const searchFlightsLink = page
      .getByRole("link", { name: "Search Flights" })
      .first();
    await expect(searchFlightsLink).toHaveAttribute(
      "href",
      "/dashboard/search/flights"
    );
    await clickAndWaitForUrl(page, searchFlightsLink, "/dashboard/search/flights");

    // Go back to dashboard
    await page.getByRole("navigation").getByRole("link", { name: "Overview" }).click();
    await expect(page).toHaveURL("/dashboard", { timeout: navigationTimeoutMs });
    const findHotelsLink = page.getByRole("link", { name: "Find Hotels" });
    await expect(findHotelsLink).toHaveAttribute("href", "/dashboard/search/hotels");
    await clickAndWaitForUrl(page, findHotelsLink, "/dashboard/search/hotels");

    // Go back and test AI Assistant
    await page.getByRole("navigation").getByRole("link", { name: "Overview" }).click();
    await expect(page).toHaveURL("/dashboard", { timeout: navigationTimeoutMs });
    const aiAssistantLink = page.getByRole("link", { name: "Ask AI Assistant" });
    await expect(aiAssistantLink).toHaveAttribute("href", "/chat");
    await expect(aiAssistantLink).toBeVisible({ timeout: navigationTimeoutMs });
    await clickAndWaitForUrl(page, aiAssistantLink, "/chat");
  });

  test("dashboard is responsive on mobile", async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ height: 667, width: 375 });

    await authenticateAsTestUser(page);
    await page.goto("/dashboard");

    // Verify dashboard renders on mobile
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

    // Verify quick actions are still accessible
    await expect(page.getByText("Search Flights").first()).toBeVisible();
  });

  test("protected routes redirect to login when not authenticated", async ({
    page,
  }) => {
    const redirectTimeout = 30_000;

    // Try to access dashboard directly without auth
    await page.goto("/dashboard");

    // Should redirect to login
    await page.waitForURL(/\/login/, { timeout: redirectTimeout });
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible({
      timeout: redirectTimeout,
    });

    // Verify other protected routes
    await page.goto("/dashboard/trips");
    await page.waitForURL(/\/login/, { timeout: redirectTimeout });

    await page.goto("/dashboard/profile");
    await page.waitForURL(/\/login/, { timeout: redirectTimeout });

    await page.goto("/chat");
    await page.waitForURL(/\/login/, { timeout: redirectTimeout });
  });
});
