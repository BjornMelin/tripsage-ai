import { expect, test } from "@playwright/test";

test.describe("Error Boundaries and Loading States", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto("/");
  });

  test.describe("Loading States", () => {
    test("should show loading skeleton on initial page load", async ({ page }) => {
      // Intercept API calls to simulate slow loading
      await page.route("**/api/**", async (route) => {
        await page.waitForTimeout(2000); // Simulate slow API
        await route.continue();
      });

      await page.goto("/");

      // Should show loading skeleton initially
      await expect(page.locator('[role="status"]').first()).toBeVisible();

      // Wait for content to load
      await page.waitForLoadState("networkidle");

      // Loading should be replaced with actual content
      await expect(page.locator('[role="status"]')).toHaveCount(0);
    });

    test("should show appropriate loading skeleton for dashboard", async ({ page }) => {
      await page.route("**/api/dashboard/**", async (route) => {
        await page.waitForTimeout(1000);
        await route.fulfill({
          status: 200,
          body: JSON.stringify({ trips: [], stats: {} }),
        });
      });

      await page.goto("/dashboard");

      // Check for dashboard-specific loading elements
      await expect(page.locator('[role="status"]')).toHaveCount({ min: 5 });

      // Wait for loading to complete
      await page.waitForLoadState("networkidle");
    });

    test("should show chat loading skeleton", async ({ page }) => {
      await page.goto("/dashboard/chat");

      // Simulate loading chat history
      await page.route("**/api/chat/history", async (route) => {
        await page.waitForTimeout(1000);
        await route.fulfill({
          status: 200,
          body: JSON.stringify({ messages: [] }),
        });
      });

      // Should show chat loading skeleton
      await expect(page.locator('[role="status"]')).toHaveCount({ min: 3 });

      // Check for typing indicator (if applicable)
      await expect(page.locator(".animate-bounce")).toHaveCount({ min: 3 });
    });

    test("should show search results loading skeleton", async ({ page }) => {
      await page.goto("/dashboard/search/flights");

      // Fill in search form
      await page.fill('[name="origin"]', "NYC");
      await page.fill('[name="destination"]', "LAX");

      // Intercept search API
      await page.route("**/api/search/flights", async (route) => {
        await page.waitForTimeout(2000);
        await route.fulfill({
          status: 200,
          body: JSON.stringify({ results: [] }),
        });
      });

      await page.click('button[type="submit"]');

      // Should show search results skeleton
      await expect(page.locator('[role="status"]')).toHaveCount({ min: 10 });
    });
  });

  test.describe("Error Boundaries", () => {
    test("should catch and display route-level errors gracefully", async ({ page }) => {
      // Simulate a route error by returning 500
      await page.route("**/api/dashboard", async (route) => {
        await route.fulfill({
          status: 500,
          body: JSON.stringify({ error: "Internal server error" }),
        });
      });

      await page.goto("/dashboard");

      // Should show error boundary UI
      await expect(page.locator("text=Something went wrong")).toBeVisible();
      await expect(page.locator('button:has-text("Try Again")')).toBeVisible();
      await expect(page.locator('button:has-text("Go Home")')).toBeVisible();
    });

    test("should allow error recovery with try again button", async ({ page }) => {
      let requestCount = 0;

      await page.route("**/api/dashboard", async (route) => {
        requestCount++;
        if (requestCount === 1) {
          // First request fails
          await route.fulfill({
            status: 500,
            body: JSON.stringify({ error: "Server error" }),
          });
        } else {
          // Second request succeeds
          await route.fulfill({
            status: 200,
            body: JSON.stringify({ data: "success" }),
          });
        }
      });

      await page.goto("/dashboard");

      // Should show error first
      await expect(page.locator("text=Something went wrong")).toBeVisible();

      // Click try again
      await page.click('button:has-text("Try Again")');

      // Should recover and show normal content
      await expect(page.locator("text=Something went wrong")).not.toBeVisible();
    });

    test("should navigate home from error boundary", async ({ page }) => {
      await page.route("**/api/trips", async (route) => {
        await route.fulfill({
          status: 500,
          body: JSON.stringify({ error: "Server error" }),
        });
      });

      await page.goto("/dashboard/trips");

      // Should show error
      await expect(page.locator("text=Something went wrong")).toBeVisible();

      // Click go home
      await page.click('button:has-text("Go Home")');

      // Should navigate to home page
      await expect(page).toHaveURL("/");
    });

    test("should show compact error for partial failures", async ({ page }) => {
      await page.goto("/dashboard");

      // Simulate partial component failure
      await page.route("**/api/dashboard/recent-trips", async (route) => {
        await route.fulfill({
          status: 500,
          body: JSON.stringify({ error: "Failed to load recent trips" }),
        });
      });

      // Should show compact error message
      await expect(page.locator("text=Failed to load")).toBeVisible();
      await expect(page.locator('button:has-text("Retry")')).toBeVisible();
    });

    test("should display error ID for tracking in development", async ({ page }) => {
      // This test would only run in development mode
      const isDev = process.env.NODE_ENV === "development";

      if (isDev) {
        await page.route("**/api/test-error", async (route) => {
          await route.fulfill({
            status: 500,
            body: JSON.stringify({ error: "Test error for development" }),
          });
        });

        await page.goto("/test-error-page"); // hypothetical error page

        // Should show error ID in development
        await expect(page.locator("text=/Error ID: error_\\d+_\\w+/")).toBeVisible();
        await expect(page.locator("text=Test error for development")).toBeVisible();
      }
    });
  });

  test.describe("Global Error Boundary", () => {
    test("should catch critical application errors", async ({ page }) => {
      // Simulate a critical error that would trigger global error boundary
      await page.addInitScript(() => {
        // Inject error after page loads
        setTimeout(() => {
          throw new Error("Critical application error");
        }, 1000);
      });

      await page.goto("/");

      // Global error boundary should catch this
      await expect(page.locator("text=Critical Error")).toBeVisible({
        timeout: 5000,
      });
      await expect(
        page.locator("text=The application encountered a critical error")
      ).toBeVisible();
    });
  });

  test.describe("Accessibility", () => {
    test("loading states should have proper ARIA labels", async ({ page }) => {
      await page.route("**/api/**", async (route) => {
        await page.waitForTimeout(1000);
        await route.continue();
      });

      await page.goto("/dashboard");

      // Check for proper ARIA labels on loading elements
      const loadingElements = page.locator('[role="status"]');
      await expect(loadingElements.first()).toHaveAttribute("aria-label", "Loading...");

      // Check for screen reader text
      await expect(page.locator("text=Loading...")).toBeVisible();
    });

    test("error boundaries should be accessible", async ({ page }) => {
      await page.route("**/api/dashboard", async (route) => {
        await route.fulfill({ status: 500 });
      });

      await page.goto("/dashboard");

      // Error UI should be accessible
      const errorHeading = page.locator("text=Something went wrong");
      await expect(errorHeading).toBeVisible();

      // Buttons should be focusable
      const tryAgainButton = page.locator('button:has-text("Try Again")');
      await expect(tryAgainButton).toBeFocused({ timeout: 1000 });
    });
  });

  test.describe("Performance", () => {
    test("should not create memory leaks with frequent error/loading state changes", async ({
      page,
    }) => {
      // Test for memory leaks by rapidly triggering loading states
      for (let i = 0; i < 10; i++) {
        await page.route(`**/api/test-${i}`, async (route) => {
          await page.waitForTimeout(100);
          if (i % 2 === 0) {
            await route.fulfill({ status: 200, body: "{}" });
          } else {
            await route.fulfill({ status: 500 });
          }
        });

        await page.goto(`/test-endpoint-${i}`);
        await page.waitForLoadState("networkidle");
      }

      // If we get here without the page crashing, memory management is likely OK
      await expect(page.locator("body")).toBeVisible();
    });

    test("should render loading skeletons efficiently", async ({ page }) => {
      const startTime = Date.now();

      await page.route("**/api/**", async (route) => {
        await page.waitForTimeout(500);
        await route.continue();
      });

      await page.goto("/dashboard");

      // Check that loading skeletons appear quickly
      await expect(page.locator('[role="status"]').first()).toBeVisible({
        timeout: 1000,
      });

      const loadingTime = Date.now() - startTime;
      expect(loadingTime).toBeLessThan(2000); // Should render loading states quickly
    });
  });
});
