import { expect, test } from "@playwright/test";
import { authenticateAsTestUser, resetTestAuth } from "./helpers/auth";
import { mockJsonRoute, mockTextStreamRoute } from "./helpers/network";

/** Expected shape of captured request body from chat stream API. */
type ChatStreamBody = {
  id?: string;
  message?: unknown;
  messages?: unknown[];
  sessionId?: string;
  trigger?: string;
  [key: string]: unknown;
};

test.describe("Budget and Memory Agents", () => {
  test.beforeEach(async ({ page }) => {
    await resetTestAuth(page);
    await authenticateAsTestUser(page);
    await page.goto("/chat");
    await mockJsonRoute(
      page,
      "**/api/chat/sessions",
      { id: "session-1" },
      {
        method: "POST",
        status: 201,
      }
    );
  });

  test("budget agent displays chart", async ({ page }) => {
    let capturedBody: ChatStreamBody | null = null;
    const handled = await mockTextStreamRoute<ChatStreamBody>(
      page,
      "**/api/chat",
      JSON.stringify({
        allocations: [
          { amount: 500, category: "Flights", rationale: "Round trip" },
          { amount: 800, category: "Accommodation", rationale: "5 nights" },
        ],
        currency: "USD",
        schemaVersion: "budget.v1",
        tips: ["Book early for better rates"],
      }),
      (body) => {
        capturedBody = body;
      }
    );

    const textarea = page.locator('textarea[aria-label="Chat prompt"]');
    await textarea.fill("Plan a budget for Paris for 5 days");
    await textarea.press("Enter");

    await expect.poll(handled, { timeout: 10000 }).toBe(true);
    expect(capturedBody).toMatchObject({ message: expect.any(Object) });

    // Wait for budget chart to appear
    await expect(page.locator("text=Budget Plan")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("text=Flights")).toBeVisible();
    await expect(page.locator("text=Accommodation")).toBeVisible();
  });

  test("memory agent confirms write", async ({ page }) => {
    let capturedBody: ChatStreamBody | null = null;
    const handled = await mockTextStreamRoute<ChatStreamBody>(
      page,
      "**/api/chat",
      "Memory stored successfully.",
      (body) => {
        capturedBody = body;
      }
    );

    // Send a message that triggers memory update
    const textarea = page.locator('textarea[aria-label="Chat prompt"]');
    await textarea.fill("Remember that I prefer window seats");
    await textarea.press("Enter");

    await expect.poll(handled, { timeout: 10000 }).toBe(true);
    expect(capturedBody).toMatchObject({ message: expect.any(Object) });

    // Wait for confirmation message
    await expect(page.locator("text=Memory stored")).toBeVisible({ timeout: 10000 });
  });
});
