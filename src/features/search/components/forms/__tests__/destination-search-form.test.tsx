/** @vitest-environment jsdom */

import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import { renderWithProviders } from "@/test/test-utils";
import { createFakeTimersContext } from "@/test/utils/with-fake-timers";
import { DestinationSearchForm } from "../destination-search-form";

const MockOnSearch = vi.fn();

vi.mock("@/hooks/use-memory", () => ({
  useMemoryContext: () => ({
    data: null,
    error: null,
    isError: false,
    isLoading: false,
    isSuccess: false,
  }),
}));

const TypeQuery = (value: string) => {
  const input = screen.getByPlaceholderText(
    "Search for cities, countries, or landmarks..."
  );
  fireEvent.change(input, { target: { value } });
  return input as HTMLInputElement;
};

const AUTOCOMPLETE_DELAY_MS = 350;

/**
 * Triggers autocomplete by typing and advancing fake timers.
 * Uses auto-advancing timers to allow promises to settle.
 */
const TriggerAutocomplete = async (value: string) => {
  const input = TypeQuery(value);
  // Advance time and allow microtasks to flush
  await act(async () => {
    vi.advanceTimersByTime(AUTOCOMPLETE_DELAY_MS);
    // Allow any pending microtasks/promises to resolve
    await vi.runAllTimersAsync();
  });
  return input;
};

describe("DestinationSearchForm", () => {
  // Use shouldAdvanceTime to allow MSW network requests to settle with fake timers
  const timers = createFakeTimersContext({ shouldAdvanceTime: true });

  beforeEach(() => {
    timers.setup();
    vi.clearAllMocks();
  });

  afterEach(() => {
    timers.teardown();
    server.resetHandlers();
  });

  it("fetches Google Places suggestions and applies selection", async () => {
    server.use(
      http.post("/api/places/search", async ({ request }) => {
        const body = (await request.json()) as { textQuery?: string };
        const textQuery = body.textQuery ?? "Paris";
        return HttpResponse.json({
          places: [
            {
              formattedAddress: `${textQuery}, France`,
              name: textQuery,
              placeId: "place-paris",
              types: ["locality", "country"],
            },
          ],
        });
      })
    );

    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);

    const input = await TriggerAutocomplete("Paris");

    const suggestion = await screen.findByRole("option", {
      name: /Paris/,
    });
    fireEvent.mouseDown(suggestion);

    expect(input.value).toBe("Paris, France");
  });

  it("filters suggestions by selected destination types", async () => {
    server.use(
      http.post("/api/places/search", () =>
        HttpResponse.json({
          places: [
            {
              formattedAddress: "Country Match, Earth",
              name: "Country Match",
              placeId: "match-1",
              types: ["country"],
            },
            {
              formattedAddress: "Museum District",
              name: "Museum Only",
              placeId: "museum-1",
              types: ["establishment"],
            },
          ],
        })
      )
    );

    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);

    await TriggerAutocomplete("Co");

    await waitFor(() =>
      expect(screen.getByRole("option", { name: /Country Match/ })).toBeInTheDocument()
    );
    expect(screen.queryByText(/Museum Only/)).not.toBeInTheDocument();
  });

  it("shows rate limit errors from the API", async () => {
    server.use(
      http.post("/api/places/search", () =>
        HttpResponse.json(
          { reason: "Too many requests. Please try again later." },
          { status: 429 }
        )
      )
    );

    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);

    await TriggerAutocomplete("Paris");

    const errorMessage = await screen.findByText(/Too many requests/);
    expect(errorMessage).toBeInTheDocument();
  });

  it("keeps latest query results when earlier requests resolve later", async () => {
    // Track request order - use object to avoid closure issues
    const slowRequest = { resolver: null as (() => void) | null };

    server.use(
      http.post("/api/places/search", async ({ request }) => {
        const body = (await request.json()) as { textQuery?: string };
        if (body.textQuery === "Pa") {
          // Hold request until manually resolved
          await new Promise<void>((resolve) => {
            slowRequest.resolver = resolve;
          });
          return HttpResponse.json({
            places: [
              {
                formattedAddress: "Old Pa Address",
                name: "Old Pa",
                placeId: "old-pa",
                types: ["locality"],
              },
            ],
          });
        }

        return HttpResponse.json({
          places: [
            {
              formattedAddress: "Paris, France",
              name: "Paris",
              placeId: "new-paris",
              types: ["locality"],
            },
          ],
        });
      })
    );

    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);

    try {
      // First query - this will be slow
      await TriggerAutocomplete("Pa");

      // Second query - this should complete first
      await TriggerAutocomplete("Paris");

      // Wait for the fast request to render
      await waitFor(() =>
        expect(screen.getByRole("option", { name: /Paris/ })).toBeInTheDocument()
      );

      // Now release the slow request
      slowRequest.resolver?.();

      // Allow pending promises to flush
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      // The old result should not replace the new one
      expect(screen.getByRole("option", { name: /Paris/ })).toBeInTheDocument();
      expect(screen.queryByText(/Old Pa/)).not.toBeInTheDocument();
    } finally {
      // Ensure the slow request is resolved even if assertions fail
      slowRequest.resolver?.();
    }
  });

  it("renders static form content", () => {
    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);

    expect(screen.getByText("Destination Search")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Discover amazing destinations around the world with intelligent autocomplete"
      )
    ).toBeInTheDocument();
    expect(screen.getByText("Popular Destinations")).toBeInTheDocument();
    expect(screen.getByText("Destination Types")).toBeInTheDocument();
  });
});
