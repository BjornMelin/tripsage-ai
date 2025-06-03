import { test, expect } from "@playwright/test";

test.describe("Dashboard Functionality", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto("/");
  });

  test("dashboard page renders correctly after authentication", async ({ page }) => {
    // Navigate to login page
    await page.goto("/login");

    // Verify login page loads
    await expect(page).toHaveTitle(/TripSage/);
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();

    // Fill in login form
    await page.fill('input[type="email"]', "test@example.com");
    await page.fill('input[type="password"]', "password123");

    // Submit login form
    await page.click('button[type="submit"]');

    // Wait for redirect to dashboard
    await page.waitForURL("/dashboard");

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

    // Take screenshot for verification
    await page.screenshot({
      path: "dashboard-authenticated.png",
      fullPage: true,
    });
  });

  test("dashboard navigation works correctly", async ({ page }) => {
    // Start from login and authenticate
    await page.goto("/login");
    await page.fill('input[type="email"]', "test@example.com");
    await page.fill('input[type="password"]', "password123");
    await page.click('button[type="submit"]');
    await page.waitForURL("/dashboard");

    // Test sidebar navigation
    await page.getByRole("navigation").getByRole("link", { name: "My Trips" }).click();
    await expect(page).toHaveURL("/dashboard/trips");

    await page.getByRole("navigation").getByRole("link", { name: "Search" }).click();
    await expect(page).toHaveURL("/dashboard/search");

    await page
      .getByRole("navigation")
      .getByRole("link", { name: "AI Assistant" })
      .click();
    await expect(page).toHaveURL("/dashboard/chat");

    // Return to dashboard home
    await page.getByRole("navigation").getByRole("link", { name: "Overview" }).click();
    await expect(page).toHaveURL("/dashboard");
  });

  test("user navigation menu works", async ({ page }) => {
    // Authenticate first
    await page.goto("/login");
    await page.fill('input[type="email"]', "test@example.com");
    await page.fill('input[type="password"]', "password123");
    await page.click('button[type="submit"]');
    await page.waitForURL("/dashboard");

    // Click on user menu
    await page.getByRole("button", { name: "User" }).click();

    // Wait for popover to be visible and target menu items within the popover content
    const popoverContent = page.locator("[data-radix-popper-content-wrapper]");
    await expect(popoverContent).toBeVisible();

    // Verify menu options using the popover container to avoid sidebar conflicts
    await expect(popoverContent.getByRole("link", { name: "Profile" })).toBeVisible();
    await expect(popoverContent.getByRole("link", { name: "Settings" })).toBeVisible();
    await expect(popoverContent.getByRole("button", { name: "Log out" })).toBeVisible();

    // Test profile navigation
    await popoverContent.getByRole("link", { name: "Profile" }).click();
    await expect(page).toHaveURL("/dashboard/profile");

    // Navigate back and test settings
    await page.goto("/dashboard");
    await page.getByRole("button", { name: "User" }).click();

    // Wait for popover again and click settings
    await expect(popoverContent).toBeVisible();
    await popoverContent.getByRole("link", { name: "Settings" }).click();
    await expect(page).toHaveURL("/dashboard/settings");
  });

  test("logout functionality works", async ({ page }) => {
    // Authenticate first
    await page.goto("/login");
    await page.fill('input[type="email"]', "test@example.com");
    await page.fill('input[type="password"]', "password123");
    await page.click('button[type="submit"]');
    await page.waitForURL("/dashboard");

    // Click on user menu and logout
    await page.getByRole("button", { name: "User" }).click();

    // Wait for popover to be visible and target logout button within it
    const popoverContent = page.locator("[data-radix-popper-content-wrapper]");
    await expect(popoverContent).toBeVisible();
    await popoverContent.getByRole("button", { name: "Log out" }).click();

    // Wait for redirect to home page (logout redirects to /)
    await page.waitForURL("/");

    // Verify we're on home page with login button (unauthenticated)
    await expect(page.getByRole("button", { name: "Log in" })).toBeVisible();

    // Verify that trying to access dashboard redirects to login
    await page.goto("/dashboard");
    await page.waitForURL(/\/login/);
    await expect(
      page.getByRole("heading", { name: "Sign in to TripSage" })
    ).toBeVisible();
  });

  test("theme toggle works", async ({ page }) => {
    // Authenticate first
    await page.goto("/login");
    await page.fill('input[type="email"]', "test@example.com");
    await page.fill('input[type="password"]', "password123");
    await page.click('button[type="submit"]');
    await page.waitForURL("/dashboard");

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
    // Authenticate first
    await page.goto("/login");
    await page.fill('input[type="email"]', "test@example.com");
    await page.fill('input[type="password"]', "password123");
    await page.click('button[type="submit"]');
    await page.waitForURL("/dashboard");

    // Test quick action navigation
    await page.getByRole("link", { name: "Search Flights" }).first().click();
    await expect(page).toHaveURL("/dashboard/search/flights");

    // Go back to dashboard
    await page.goto("/dashboard");
    await page.getByRole("link", { name: "Find Hotels" }).click();
    await expect(page).toHaveURL("/dashboard/search/hotels");

    // Go back and test AI Assistant
    await page.goto("/dashboard");
    await page.getByRole("link", { name: "Ask AI Assistant" }).click();
    await expect(page).toHaveURL("/dashboard/chat");
  });

  test("dashboard is responsive on mobile", async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Authenticate
    await page.goto("/login");
    await page.fill('input[type="email"]', "test@example.com");
    await page.fill('input[type="password"]', "password123");
    await page.click('button[type="submit"]');
    await page.waitForURL("/dashboard");

    // Verify dashboard renders on mobile
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

    // Verify quick actions are still accessible
    await expect(page.getByText("Search Flights").first()).toBeVisible();

    // Take mobile screenshot
    await page.screenshot({
      path: "dashboard-mobile.png",
      fullPage: true,
    });
  });

  test("protected routes redirect to login when not authenticated", async ({
    page,
  }) => {
    // Try to access dashboard directly without auth
    await page.goto("/dashboard");

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();

    // Verify other protected routes
    await page.goto("/dashboard/trips");
    await expect(page).toHaveURL(/\/login/);

    await page.goto("/dashboard/profile");
    await expect(page).toHaveURL(/\/login/);

    await page.goto("/dashboard/chat");
    await expect(page).toHaveURL(/\/login/);
  });
});
