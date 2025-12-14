import { expect, test } from "@playwright/test";
import { authenticateAsTestUser, resetTestAuth } from "./helpers/auth";

/** Expected shape of captured request body from chat stream API. */
type ChatStreamBody = {
  messages?: unknown[];
  [key: string]: unknown;
};

test.describe("Budget and Memory Agents", () => {
  test.beforeEach(async ({ page }) => {
    await resetTestAuth(page);
    await authenticateAsTestUser(page);
    await page.goto("/chat");
  });

  test("budget agent displays chart", async ({ page }) => {
    let handled = false;
    let capturedBody: ChatStreamBody | null = null;
    await page.route("**/api/chat/stream**", async (route) => {
      const request = route.request();
      handled = true;
      const body = (() => {
        try {
          return request.postDataJSON() as ChatStreamBody;
        } catch {
          return {} as ChatStreamBody;
        }
      })();
      capturedBody = body;

      const text = JSON.stringify({
        allocations: [
          { amount: 500, category: "Flights", rationale: "Round trip" },
          { amount: 800, category: "Accommodation", rationale: "5 nights" },
        ],
        currency: "USD",
        schemaVersion: "budget.v1",
        tips: ["Book early for better rates"],
      });

      await route.fulfill({
        body: `data: ${JSON.stringify({ messageId: "assistant-1", type: "start" })}\n\ndata: ${JSON.stringify({ id: "text-1", type: "text-start" })}\n\ndata: ${JSON.stringify({ delta: text, id: "text-1", type: "text-delta" })}\n\ndata: ${JSON.stringify({ id: "text-1", type: "text-end" })}\n\ndata: ${JSON.stringify({ finishReason: "stop", type: "finish" })}\n\ndata: [DONE]\n\n`,
        contentType: "text/event-stream",
        headers: { "x-vercel-ai-ui-message-stream": "v1" },
        status: 200,
      });
    });

    const textarea = page.locator('textarea[aria-label="Chat prompt"]');
    await textarea.fill("Plan a budget for Paris for 5 days");
    await textarea.press("Enter");

    await expect.poll(() => handled).toBe(true);
    expect(capturedBody).toMatchObject({ messages: expect.any(Array) });

    // Wait for budget chart to appear
    await expect(page.locator("text=Budget Plan")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("text=Flights")).toBeVisible();
    await expect(page.locator("text=Accommodation")).toBeVisible();
  });

  test("memory agent confirms write", async ({ page }) => {
    let handled = false;
    let capturedBody: ChatStreamBody | null = null;
    await page.route("**/api/chat/stream**", async (route) => {
      const request = route.request();
      handled = true;
      const body = (() => {
        try {
          return request.postDataJSON() as ChatStreamBody;
        } catch {
          return {} as ChatStreamBody;
        }
      })();
      capturedBody = body;

      await route.fulfill({
        body: `data: ${JSON.stringify({ messageId: "assistant-1", type: "start" })}\n\ndata: ${JSON.stringify({ id: "text-1", type: "text-start" })}\n\ndata: ${JSON.stringify({ delta: "Memory stored successfully.", id: "text-1", type: "text-delta" })}\n\ndata: ${JSON.stringify({ id: "text-1", type: "text-end" })}\n\ndata: ${JSON.stringify({ finishReason: "stop", type: "finish" })}\n\ndata: [DONE]\n\n`,
        contentType: "text/event-stream",
        headers: { "x-vercel-ai-ui-message-stream": "v1" },
        status: 200,
      });
    });

    // Send a message that triggers memory update
    const textarea = page.locator('textarea[aria-label="Chat prompt"]');
    await textarea.fill("Remember that I prefer window seats");
    await textarea.press("Enter");

    await expect.poll(() => handled).toBe(true);
    expect(capturedBody).toMatchObject({ messages: expect.any(Array) });

    // Wait for confirmation message
    await expect(page.locator("text=Memory stored")).toBeVisible({ timeout: 10000 });
  });
});
