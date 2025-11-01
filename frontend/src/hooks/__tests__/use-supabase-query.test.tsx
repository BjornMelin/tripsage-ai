/**
 * @fileoverview Tests for the useSupabaseQuery hook.
 */

import { waitFor } from "@testing-library/react";
import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSupabaseQuery } from "@/hooks/use-supabase-query";
import type { Database } from "@/lib/supabase/database.types";
import { createMockSupabaseClient } from "@/test/mock-helpers";
import { render } from "@/test/test-utils";

type TripsTable = Database["public"]["Tables"]["trips"]["Row"];

const supabase = createMockSupabaseClient();
const fromMock = supabase.from as unknown as Mock;

vi.mock("@/lib/supabase/client", () => ({
  useSupabase: () => supabase,
  getBrowserClient: () => supabase,
  createClient: () => supabase,
}));

const createSelectBuilder = (rows: TripsTable[]) => {
  const result = { data: rows, error: null };
  return {
    select: vi.fn().mockReturnThis(),
    eq: vi.fn().mockReturnThis(),
    order: vi.fn().mockReturnThis(),
    range: vi.fn().mockReturnThis(),
    then: (
      onFulfilled?: (value: typeof result) => unknown,
      onRejected?: (reason: unknown) => unknown
    ) => Promise.resolve(result).then(onFulfilled, onRejected),
  };
};

const createTripRow = (overrides: Partial<TripsTable> = {}): TripsTable => ({
  id: overrides.id ?? 1,
  user_id: overrides.user_id ?? "test-user-id",
  name: overrides.name ?? "Test Trip",
  start_date: overrides.start_date ?? "2025-01-01",
  end_date: overrides.end_date ?? "2025-01-05",
  destination: overrides.destination ?? "Paris",
  budget: overrides.budget ?? 1200,
  travelers: overrides.travelers ?? 2,
  status: overrides.status ?? "planning",
  trip_type: overrides.trip_type ?? "leisure",
  flexibility: overrides.flexibility ?? {},
  notes: overrides.notes ?? null,
  search_metadata: overrides.search_metadata ?? {},
  created_at: overrides.created_at ?? new Date(0).toISOString(),
  updated_at: overrides.updated_at ?? new Date(0).toISOString(),
});

function UsersList() {
  const { data, isSuccess } = useSupabaseQuery({
    table: "trips",
    columns: "id",
  });
  return <div data-testid="count">{isSuccess ? (data?.length ?? 0) : "-"}</div>;
}

describe("useSupabaseQuery", () => {
  beforeEach(() => {
    fromMock.mockReset();
  });

  it("fetches when user exists and returns data", async () => {
    const trips: TripsTable[] = [
      createTripRow({ id: 1, name: "Trip 1" }),
      createTripRow({ id: 2, name: "Trip 2" }),
    ];

    fromMock.mockImplementationOnce((table: string) => {
      expect(table).toBe("trips");
      return createSelectBuilder(trips);
    });

    const { getByTestId } = render(<UsersList />);

    await waitFor(() => {
      expect(getByTestId("count")).toHaveTextContent("2");
    });
  });
});
