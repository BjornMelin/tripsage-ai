import { vi } from "vitest";
import type { SupabaseClient } from "@supabase/supabase-js";

// Global storage for mock data that persists across client instances
const globalMockData: Record<string, any[]> = {
  trips: [],
};

// Helper to generate trip data
const generateTripData = (data: any) => {
  const id = Date.now() + Math.floor(Math.random() * 1000);
  const now = new Date().toISOString();
  return {
    id,
    uuid_id: `uuid-${id}`,
    user_id: "test-user-id",
    title: data.title || data.name || "Untitled Trip",
    name: data.title || data.name || "Untitled Trip",
    description: data.description || "",
    start_date: data.startDate || data.start_date || null,
    end_date: data.endDate || data.end_date || null,
    destination: data.destination || null,
    budget: data.budget || null,
    currency: data.currency || "USD",
    spent_amount: data.spent_amount || 0,
    visibility: data.visibility || "private",
    tags: data.tags || [],
    preferences: data.preferences || {},
    status: data.status || "planning",
    budget_breakdown: data.enhanced_budget || null,
    created_at: now,
    updated_at: now,
  };
};

// Create a mock Supabase client specifically for trip store tests
export const createTripStoreMockClient = (): Partial<SupabaseClient> => {
  return {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: {
          session: {
            user: { id: "test-user-id" },
            access_token: "test-token",
          },
        },
        error: null,
      }),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
      signUp: vi.fn().mockResolvedValue({ data: null, error: null }),
      signInWithPassword: vi.fn().mockResolvedValue({ data: null, error: null }),
      signOut: vi.fn().mockResolvedValue({ error: null }),
      resetPasswordForEmail: vi.fn().mockResolvedValue({ data: null, error: null }),
      updateUser: vi.fn().mockResolvedValue({ data: null, error: null }),
    } as SupabaseClient["auth"],
    from: vi.fn((table: string) => {
      const builder: any = {
        select: vi.fn(() => {
          // For select queries, return the data from global storage
          builder._isSelect = true;
          return builder;
        }),
        insert: vi.fn((data: any[]) => {
          // Handle insert operations
          const insertedData = data.map((item) => generateTripData(item));
          globalMockData[table] = [...(globalMockData[table] || []), ...insertedData];
          builder._insertedData = insertedData;
          builder._isInsert = true;
          return builder;
        }),
        update: vi.fn((data: any) => {
          builder._updateData = data;
          builder._isUpdate = true;
          return builder;
        }),
        delete: vi.fn(() => {
          builder._isDelete = true;
          return builder;
        }),
        eq: vi.fn((column: string, value: any) => {
          builder._filters = builder._filters || [];
          builder._filters.push({ column, value });
          return builder;
        }),
        order: vi.fn(() => builder),
        range: vi.fn(() => builder),
        single: vi.fn(() => {
          if (
            builder._isInsert &&
            builder._insertedData &&
            builder._insertedData.length === 1
          ) {
            return Promise.resolve({ data: builder._insertedData[0], error: null });
          }
          if (builder._isSelect || builder._isUpdate || builder._isDelete) {
            const tableData = globalMockData[table] || [];
            let result = tableData;

            // Apply filters
            if (builder._filters) {
              builder._filters.forEach((filter: any) => {
                result = result.filter((item) => item[filter.column] === filter.value);
              });
            }

            // Handle update
            if (builder._isUpdate && result.length > 0) {
              const updatedItem = {
                ...result[0],
                ...builder._updateData,
                updated_at: new Date().toISOString(),
              };
              const index = tableData.findIndex((item) => item.id === result[0].id);
              if (index !== -1) {
                globalMockData[table][index] = updatedItem;
              }
              return Promise.resolve({ data: updatedItem, error: null });
            }

            // Handle delete
            if (builder._isDelete && result.length > 0) {
              globalMockData[table] = tableData.filter(
                (item) => item.id !== result[0].id
              );
              return Promise.resolve({ data: result[0], error: null });
            }

            return Promise.resolve({ data: result[0] || null, error: null });
          }
          return Promise.resolve({ data: null, error: null });
        }),
        maybeSingle: vi.fn(() => builder.single()),
      };

      // Make the builder itself a thenable for select queries
      builder.then = (onFulfilled: any) => {
        if (builder._isSelect) {
          return Promise.resolve({
            data: globalMockData[table] || [],
            error: null,
          }).then(onFulfilled);
        }
        return Promise.resolve({ data: null, error: null }).then(onFulfilled);
      };

      return builder;
    }),
    channel: vi.fn().mockReturnValue({
      on: vi.fn().mockReturnThis(),
      subscribe: vi.fn().mockReturnValue({
        unsubscribe: vi.fn(),
      }),
    }),
    removeChannel: vi.fn(),
  };
};

// Reset mock data between tests
export const resetTripStoreMockData = () => {
  Object.keys(globalMockData).forEach((key) => {
    globalMockData[key] = [];
  });
};

// Helper to pre-populate mock data
export const populateTripStoreMockData = (table: string, data: any[]) => {
  globalMockData[table] = data;
};
