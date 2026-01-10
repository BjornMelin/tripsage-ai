import { expect, type Locator, type Page, test } from "@playwright/test";
import { authenticateAsTestUser, resetTestAuth } from "./helpers/auth";

const navigationTimeoutMs = 15_000;
const visibilityTimeoutMs = navigationTimeoutMs;

function getUserMenuTrigger(page: Page): Locator {
  return page
    .getByRole("banner")
    .getByRole("button", { name: /Test User|test@example\.com|User/i });
}

async function openUserMenu(page: Page): Promise<Locator> {
  const trigger = getUserMenuTrigger(page);
  await expect(trigger).toBeVisible({ timeout: visibilityTimeoutMs });

  const logoutButton = page.getByRole("button", { name: "Log out" });
  const popoverContent = page.getByRole("dialog").filter({ has: logoutButton });

  for (let attempt = 0; attempt < 2; attempt++) {
    await trigger.click();
    try {
      await expect(popoverContent).toBeVisible({ timeout: visibilityTimeoutMs });
      await expect(popoverContent).toHaveAttribute("data-state", "open", {
        timeout: visibilityTimeoutMs,
      });
      return popoverContent;
    } catch (error) {
      if (attempt === 1) throw error;
      await page.waitForTimeout(200);
    }
  }

  return popoverContent;
}

async function clickAndWaitForUrl(
  page: Page,
  locator: Locator,
  url: string | RegExp,
  options: { attempts?: number; retryDelayMs?: number; timeoutMs?: number } = {}
): Promise<void> {
  const attempts = options.attempts ?? 2;
  const retryDelayMs = options.retryDelayMs ?? 300;
  const timeoutMs = options.timeoutMs ?? navigationTimeoutMs;

  for (let attempt = 0; attempt < attempts; attempt++) {
    await locator.click({ force: attempt > 0, timeout: timeoutMs });
    try {
      await expect(page).toHaveURL(url, { timeout: timeoutMs });
      return;
    } catch (error) {
      if (attempt === attempts - 1) {
        throw error;
      }
      // Allow in-flight navigation or state changes to settle before retrying
      await page.waitForTimeout(retryDelayMs);
    }
  }
}

test.describe("Dashboard Functionality", () => {
  test.describe.configure({ timeout: 60_000 });

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
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });

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
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
    const navigation = page.getByRole("navigation");

    // Test sidebar navigation
    await clickAndWaitForUrl(
      page,
      navigation.getByRole("link", { name: "My Trips" }),
      "/dashboard/trips"
    );

    await clickAndWaitForUrl(
      page,
      navigation.getByRole("link", { name: "Search" }),
      "/dashboard/search"
    );
    await expect(page.getByRole("heading", { level: 1, name: "Search" })).toBeVisible({
      timeout: navigationTimeoutMs,
    });

    await clickAndWaitForUrl(
      page,
      navigation.getByRole("link", { name: "AI Assistant" }),
      "/chat"
    );

    // Return to dashboard home from /chat
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL("/dashboard", { timeout: navigationTimeoutMs });
  });

  test("user navigation menu works", async ({ page }) => {
    test.setTimeout(60_000);

    await authenticateAsTestUser(page);
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });

    await expect(
      page.getByRole("banner").getByRole("button", { name: "Toggle theme" })
    ).toBeVisible({ timeout: visibilityTimeoutMs });

    const popoverContent = await openUserMenu(page);

    // Verify menu options using the popover container to avoid sidebar conflicts
    await expect(popoverContent.getByRole("link", { name: "Profile" })).toBeVisible({
      timeout: visibilityTimeoutMs,
    });
    await expect(popoverContent.getByRole("link", { name: "Settings" })).toBeVisible({
      timeout: visibilityTimeoutMs,
    });
    await expect(popoverContent.getByRole("button", { name: "Log out" })).toBeVisible({
      timeout: visibilityTimeoutMs,
    });

    // Test profile navigation
    await clickAndWaitForUrl(
      page,
      popoverContent.getByRole("link", { name: "Profile" }),
      "/dashboard/profile"
    );
    await page.waitForLoadState("domcontentloaded");

    // Navigate back and test settings
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });

    await expect(
      page.getByRole("banner").getByRole("button", { name: "Toggle theme" })
    ).toBeVisible({ timeout: visibilityTimeoutMs });

    const settingsPopover = await openUserMenu(page);
    await clickAndWaitForUrl(
      page,
      settingsPopover.getByRole("link", { name: "Settings" }),
      "/dashboard/settings"
    );
  });

  test("logout functionality works", async ({ page }) => {
    await authenticateAsTestUser(page);
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });

    const popoverContent = await openUserMenu(page);
    await popoverContent.getByRole("button", { name: "Log out" }).click();

    // Wait for redirect to login page
    await page.waitForURL(/\/login/, { timeout: navigationTimeoutMs });
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible({
      timeout: visibilityTimeoutMs,
    });

    // Verify that trying to access dashboard redirects to login
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
    await page.waitForURL(/\/login/, { timeout: navigationTimeoutMs });
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible({
      timeout: visibilityTimeoutMs,
    });
  });

  test("theme toggle works", async ({ page }) => {
    await authenticateAsTestUser(page);
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });

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
    test.setTimeout(60_000);

    await authenticateAsTestUser(page);
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });

    // Test quick action navigation
    const searchFlightsLink = page
      .getByRole("main")
      .getByRole("link", { name: "Search Flights" })
      .first();
    await expect(searchFlightsLink).toHaveAttribute(
      "href",
      "/dashboard/search/flights",
      {
        timeout: visibilityTimeoutMs,
      }
    );
    await clickAndWaitForUrl(page, searchFlightsLink, "/dashboard/search/flights");

    // Go back to dashboard
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL("/dashboard", { timeout: navigationTimeoutMs });

    const findHotelsLink = page
      .getByRole("main")
      .getByRole("link", { name: "Find Hotels" });
    await expect(findHotelsLink).toHaveAttribute("href", "/dashboard/search/hotels", {
      timeout: visibilityTimeoutMs,
    });
    await clickAndWaitForUrl(page, findHotelsLink, "/dashboard/search/hotels");

    // Go back and test AI Assistant
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL("/dashboard", { timeout: navigationTimeoutMs });

    const aiAssistantLink = page
      .getByRole("main")
      .getByRole("link", { name: "Ask AI Assistant" });
    await expect(aiAssistantLink).toHaveAttribute("href", "/chat", {
      timeout: visibilityTimeoutMs,
    });
    await expect(aiAssistantLink).toBeVisible({ timeout: visibilityTimeoutMs });
    await clickAndWaitForUrl(page, aiAssistantLink, "/chat");
  });

  test("dashboard is responsive on mobile", async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ height: 667, width: 375 });

    await authenticateAsTestUser(page);
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });

    // Verify dashboard renders on mobile
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

    // Verify quick actions are still accessible
    await expect(page.getByText("Search Flights").first()).toBeVisible();
  });

  test("protected routes redirect to login when not authenticated", async ({
    page,
  }) => {
    // Try to access dashboard directly without auth
    await page.goto("/dashboard");

    // Should redirect to login
    await page.waitForURL(/\/login/, { timeout: navigationTimeoutMs });
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible({
      timeout: navigationTimeoutMs,
    });

    // Verify other protected routes
    await page.goto("/dashboard/trips");
    await page.waitForURL(/\/login/, { timeout: navigationTimeoutMs });

    await page.goto("/dashboard/profile");
    await page.waitForURL(/\/login/, { timeout: navigationTimeoutMs });

    await page.goto("/chat");
    await page.waitForURL(/\/login/, { timeout: navigationTimeoutMs });
  });
});
