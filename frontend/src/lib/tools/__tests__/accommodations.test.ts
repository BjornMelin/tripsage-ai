import { afterEach, beforeEach, expect, test, vi } from "vitest";

vi.mock("../approvals", () => ({
  requireApproval: vi.fn(),
}));

const env = process.env;

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
  process.env = {
    ...env,
    ACCOM_SEARCH_TOKEN: "test_token",
    ACCOM_SEARCH_URL: "https://api.example.com/search",
  };
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
  process.env = env;
});

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

test("searchAccommodations includes zero priceMin in query params", async () => {
  const mockRes = {
    json: async () => ({ accommodations: [] }),
    ok: true,
  } as Response;
  (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
  const { searchAccommodations } = await import("../accommodations");
  await searchAccommodations.execute?.(
    {
      checkin: "2025-07-01",
      checkout: "2025-07-05",
      guests: 2,
      location: "Paris",
      priceMax: 100,
      priceMin: 0,
    },
    mockContext
  );
  const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
  const url = new URL(call[0] as string);
  expect(url.searchParams.get("priceMin")).toBe("0");
  expect(url.searchParams.get("priceMax")).toBe("100");
});

test("searchAccommodations omits undefined price filters", async () => {
  const mockRes = {
    json: async () => ({ accommodations: [] }),
    ok: true,
  } as Response;
  (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
  const { searchAccommodations } = await import("../accommodations");
  await searchAccommodations.execute?.(
    {
      checkin: "2025-07-01",
      checkout: "2025-07-05",
      guests: 2,
      location: "Paris",
    },
    mockContext
  );
  const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
  const url = new URL(call[0] as string);
  expect(url.searchParams.has("priceMin")).toBe(false);
  expect(url.searchParams.has("priceMax")).toBe(false);
});

test("searchAccommodations throws when not configured", async () => {
  process.env.ACCOM_SEARCH_URL = "";
  process.env.AIRBNB_MCP_URL = "";
  const { searchAccommodations } = await import("../accommodations");
  await expect(
    searchAccommodations.execute?.(
      {
        checkin: "2025-07-01",
        checkout: "2025-07-05",
        guests: 2,
        location: "Paris",
      },
      mockContext
    )
  ).rejects.toThrow(/accom_search_not_configured/);
});

test("bookAccommodation returns pending_confirmation status", async () => {
  const { requireApproval } = await import("../approvals");
  (requireApproval as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);
  const { bookAccommodation } = await import("../accommodations");
  const result = await bookAccommodation.execute?.(
    {
      checkin: "2025-07-01",
      checkout: "2025-07-05",
      guests: 2,
      listingId: "listing-123",
      sessionId: "session-456",
    },
    mockContext
  );
  expect(result).toHaveProperty("status", "pending_confirmation");
  expect(result).toHaveProperty("message");
  expect((result as { message?: string }).message).toContain("pending");
});

test("bookAccommodation requires approval", async () => {
  const { requireApproval } = await import("../approvals");
  (requireApproval as ReturnType<typeof vi.fn>).mockRejectedValue(
    new Error("approval_required")
  );
  const { bookAccommodation } = await import("../accommodations");
  await expect(
    bookAccommodation.execute?.(
      {
        checkin: "2025-07-01",
        checkout: "2025-07-05",
        guests: 2,
        listingId: "listing-123",
        sessionId: "session-456",
      },
      mockContext
    )
  ).rejects.toThrow(/approval_required/);
});
