import { waitFor } from "@testing-library/react";
import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSupabaseQuery } from "@/hooks/use-supabase-query";
import type { Database } from "@/lib/supabase/database.types";
import { createMockSupabaseClient } from "@/test/mock-helpers.test";
import { render } from "@/test/test-utils.test";

type TripsTable = Database["public"]["Tables"]["trips"]["Row"];

const SUPABASE = createMockSupabaseClient();
const FROM_MOCK = SUPABASE.from as unknown as Mock;

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => SUPABASE,
  getBrowserClient: () => SUPABASE,
  useSupabase: () => SUPABASE,
}));

const CREATE_SELECT_BUILDER = (rows: TripsTable[]) => {
  const result = { data: rows, error: null };

  // Create a mock builder that behaves like a Promise
  const builder = {
    eq: vi.fn().mockReturnThis(),
    order: vi.fn().mockReturnThis(),
    range: vi.fn().mockReturnThis(),
    select: vi.fn().mockReturnThis(),
    // biome-ignore lint/suspicious/noThenProperty: Mock needs Promise-like then method
    then: vi
      .fn()
      .mockImplementation((onFulfilled: (value: typeof result) => unknown) =>
        Promise.resolve(result).then(onFulfilled)
      ),
  };

  return builder;
};

const CREATE_TRIP_ROW = (overrides: Partial<TripsTable> = {}): TripsTable => ({
  budget: overrides.budget ?? 1200,
  created_at: overrides.created_at ?? new Date(0).toISOString(),
  destination: overrides.destination ?? "Paris",
  end_date: overrides.end_date ?? "2025-01-05",
  flexibility: overrides.flexibility ?? {},
  id: overrides.id ?? 1,
  name: overrides.name ?? "Test Trip",
  notes: overrides.notes ?? null,
  search_metadata: overrides.search_metadata ?? {},
  start_date: overrides.start_date ?? "2025-01-01",
  status: overrides.status ?? "planning",
  travelers: overrides.travelers ?? 2,
  trip_type: overrides.trip_type ?? "leisure",
  updated_at: overrides.updated_at ?? new Date(0).toISOString(),
  user_id: overrides.user_id ?? "test-user-id",
});

function UsersList() {
  const { data, isSuccess } = useSupabaseQuery({
    columns: "id",
    table: "trips",
  });
  return <div data-testid="count">{isSuccess ? (data?.length ?? 0) : "-"}</div>;
}

describe("useSupabaseQuery", () => {
  beforeEach(() => {
    FROM_MOCK.mockReset();
  });

  it("fetches when user exists and returns data", async () => {
    const trips: TripsTable[] = [
      CREATE_TRIP_ROW({ id: 1, name: "Trip 1" }),
      CREATE_TRIP_ROW({ id: 2, name: "Trip 2" }),
    ];

    FROM_MOCK.mockImplementationOnce((table: string) => {
      expect(table).toBe("trips");
      return CREATE_SELECT_BUILDER(trips);
    });

    const { getByTestId } = render(<UsersList />);

    await waitFor(() => {
      expect(getByTestId("count")).toHaveTextContent("2");
    });
  });
});
