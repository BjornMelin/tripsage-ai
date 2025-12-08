import { expect, test } from "@playwright/test";

test.describe("Budget and Memory Agents", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/chat");
  });

  test("budget agent displays chart", async ({ page }) => {
    // Wait for chat interface to load
    await page.waitForSelector('[data-testid^="msg-"]', { timeout: 5000 }).catch(() => {
      // Chat may be empty initially
    });

    // Mock the API response for budget agent
    await page.route("**/api/agents/budget", async (route) => {
      const request = route.request();
      const body = await request.postDataJSON();
      expect(body).toMatchObject({
        destination: expect.any(String),
        durationDays: expect.any(Number),
      });

      // Return a mock streaming response with budget result
      await route.fulfill({
        body: `data: {"type":"text","text":"{\\"schemaVersion\\":\\"budget.v1\\",\\"currency\\":\\"USD\\",\\"allocations\\":[{\\"category\\":\\"Flights\\",\\"amount\\":500,\\"rationale\\":\\"Round trip\\"},{\\"category\\":\\"Accommodation\\",\\"amount\\":800,\\"rationale\\":\\"5 nights\\"}],\\"tips\\":[\\"Book early for better rates\\"]}"}\n\ndata: {"type":"finish"}\n\n`,
        contentType: "text/event-stream",
        status: 200,
      });
    });

    // Trigger budget agent via quick action menu
    await page.click('button[aria-label="More actions"]');
    await page.click("text=Plan budget");

    // Wait for budget chart to appear
    await expect(page.locator("text=Budget Plan")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("text=Flights")).toBeVisible();
    await expect(page.locator("text=Accommodation")).toBeVisible();
  });

  test("memory agent confirms write", async ({ page }) => {
    // Wait for chat interface to load
    await page.waitForSelector('[data-testid^="msg-"]', { timeout: 5000 }).catch(() => {
      // Chat may be empty initially
    });

    // Mock the API response for memory agent
    await page.route("**/api/agents/memory", async (route) => {
      const request = route.request();
      const body = await request.postDataJSON();
      expect(body).toMatchObject({
        records: expect.arrayContaining([
          expect.objectContaining({
            content: expect.any(String),
          }),
        ]),
      });

      // Return a mock streaming response with confirmation
      await route.fulfill({
        body: `data: {"type":"text","text":"Memory stored successfully."}\n\ndata: {"type":"finish"}\n\n`,
        contentType: "text/event-stream",
        status: 200,
      });
    });

    // Send a message that triggers memory update
    const textarea = page.locator('textarea[aria-label="Chat prompt"]');
    await textarea.fill("Remember that I prefer window seats");
    await textarea.press("Enter");

    // Wait for confirmation message
    await expect(page.locator("text=Memory stored")).toBeVisible({ timeout: 10000 });
  });
});
