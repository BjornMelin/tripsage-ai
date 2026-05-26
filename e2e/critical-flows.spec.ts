import { expect, type Page, test } from "@playwright/test";
import { authenticateAsTestUser, resetTestAuth } from "./helpers/auth";
import { fulfillJson, mockJsonRoute } from "./helpers/network";

const JOB_ROUTES = [
  "/api/jobs/attachments-ingest",
  "/api/jobs/memory-sync",
  "/api/jobs/notify-collaborators",
  "/api/jobs/rag-index",
] as const;

const GUARDED_POST_ROUTES = [
  {
    body: { apiKey: "sk-smoke-placeholder", service: "openai" },
    label: "BYOK validation guard",
    path: "/api/keys/validate",
  },
  {
    body: {
      chatId: "chat-critical-smoke",
      files: [
        {
          contentType: "application/pdf",
          originalName: "itinerary.pdf",
          size: 1024,
        },
      ],
    },
    label: "attachment upload guard",
    path: "/api/chat/attachments",
  },
  ...JOB_ROUTES.map((path) => ({
    body: {},
    label: `${path} unsigned QStash guard`,
    path,
  })),
] as const;

function dateInputDaysFromNow(days: number): string {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

async function mockCriticalProviderRoutes(page: Page): Promise<{
  flightSearchRequests: () => number;
}> {
  let flightSearchRequests = 0;

  await mockJsonRoute(page, "**/api/flights/popular-routes", [
    { date: "Jun 18", destination: "LAX", origin: "SFO", price: 188 },
    { date: "Jul 4", destination: "JFK", origin: "DEN", price: 244 },
  ]);
  await mockJsonRoute(page, "**/api/flights/popular-destinations", [
    { code: "LAX", country: "US", name: "Los Angeles", savings: "$89" },
    { code: "JFK", country: "US", name: "New York", savings: "$127" },
  ]);

  await page.route("**/api/flights/search", async (route) => {
    flightSearchRequests += 1;
    await fulfillJson(route, {
      itineraries: [
        {
          id: "flight-critical-1",
          price: 188,
          segments: [
            {
              arrival: `${dateInputDaysFromNow(45)}T12:00:00.000Z`,
              carrier: "TestAir",
              departure: `${dateInputDaysFromNow(45)}T10:00:00.000Z`,
              destination: "LAX",
              flightNumber: "TS123",
              origin: "SFO",
            },
          ],
        },
      ],
      provider: "E2E",
    });
  });

  await mockJsonRoute(page, "**/api/calendar/status", { connected: false });
  await mockJsonRoute(page, "**/api/calendar/events**", { items: [] });
  await mockJsonRoute(page, "**/api/keys", [], { method: "GET" });
  await mockJsonRoute(page, "**/api/user-settings", { allowGatewayFallback: true });

  return {
    flightSearchRequests: () => flightSearchRequests,
  };
}

test.describe("Critical production flows", () => {
  test.beforeEach(async ({ page }) => {
    await resetTestAuth(page);
  });

  test("keeps unauthenticated deployment and job routes guarded", async ({
    request,
  }) => {
    const health = await request.get("/api/health");
    await expect(health).toBeOK();
    expect(health.headers()["cache-control"]).toMatch(/no-store/i);
    await expect(await health.json()).toMatchObject({
      service: "tripsage-ai",
      status: "ok",
    });

    const auth = await request.get("/auth/me", { maxRedirects: 0 });
    expect(auth.status()).toBe(401);

    for (const route of GUARDED_POST_ROUTES) {
      const response = await request.post(route.path, {
        data: route.body,
        maxRedirects: 0,
      });
      expect(response.status(), route.label).toBe(401);
    }

    const byokHealth = await request.get("/api/health/byok", { maxRedirects: 0 });
    expect(byokHealth.headers()["cache-control"]).toMatch(/no-store/i);
    expect([401, 503], "BYOK health requires operator setup or key").toContain(
      byokHealth.status()
    );
  });

  test("runs search, calendar, and BYOK UI shells with deterministic providers", async ({
    page,
  }) => {
    test.setTimeout(60_000);
    const providerMocks = await mockCriticalProviderRoutes(page);
    await authenticateAsTestUser(page);

    await page.goto("/dashboard/search/flights", { waitUntil: "domcontentloaded" });
    await expect(
      page.getByRole("heading", { level: 3, name: "Search Flights" })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Find Flights" })).toBeVisible();
    await expect(page.getByText("SFO")).toBeVisible();

    await page.getByRole("textbox", { name: "From" }).fill("SFO");
    await page.getByRole("textbox", { name: "To" }).fill("LAX");
    await page
      .getByRole("textbox", { name: "Departure" })
      .fill(dateInputDaysFromNow(45));
    await page.getByRole("textbox", { name: "Return" }).fill(dateInputDaysFromNow(52));
    await page.getByRole("button", { name: "Search Flights" }).click();
    await expect
      .poll(providerMocks.flightSearchRequests, {
        message: "flight search API request should be issued",
        timeout: 15_000,
      })
      .toBe(1);
    await expect(page.getByText("Search Started")).toBeVisible();
    await expect
      .poll(() => page.url(), {
        message: "flight results URL should be committed",
        timeout: 15_000,
      })
      .toMatch(/\/dashboard\/search\/flights\/results\?searchId=/);
    await page.waitForLoadState("domcontentloaded", {
      timeout: 15_000,
    });
    await expect(
      page.getByRole("heading", { name: "Flight Search Results" })
    ).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("TestAir", { exact: true })).toBeVisible();
    await expect(page.getByText("TS123")).toBeVisible();
    await expect(
      page.getByRole("button", {
        name: "Select TestAir TS123 from SFO to LAX",
      })
    ).toBeVisible();

    await page.goto("/dashboard/calendar", { waitUntil: "domcontentloaded" });
    await expect(
      page.getByRole("heading", { level: 2, name: "Calendar" })
    ).toBeVisible();
    await expect(page.getByText("Calendar Not Connected")).toBeVisible();

    await page.goto("/dashboard/settings/api-keys", {
      waitUntil: "domcontentloaded",
    });
    await expect(
      page.getByRole("heading", { name: /Bring Your Own Key/ })
    ).toBeVisible();
    await expect(page.getByRole("combobox", { name: "Provider" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("textbox", { name: "API Key" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(
      page.getByRole("switch", { name: "Allow fallback to team Gateway" })
    ).toHaveAccessibleDescription(
      /When no BYOK key is present, permit using the team Vercel AI Gateway\.\s+You can change this at any time\./
    );
  });
});
