/**
 * @fileoverview Shared test utilities for calendar API route tests.
 *
 * Provides reusable mocks and helpers to reduce duplication and improve
 * test performance through shared setup.
 */

import type { NextRequest } from "next/server";
import { vi } from "vitest";

/**
 * Mock rate limit result for successful requests.
 */
export const MOCK_RATE_LIMIT_SUCCESS = {
  limit: 60,
  remaining: 59,
  reset: Date.now() + 60000,
  success: true,
} as const;

/**
 * Mock rate limit result for rate-limited requests.
 */
export const MOCK_RATE_LIMIT_FAILED = {
  limit: 60,
  remaining: 0,
  reset: Date.now() + 60000,
  success: false,
} as const;

/**
 * Mock Supabase client for authenticated users.
 */
export const MOCK_SUPABASE_AUTHENTICATED = {
  auth: {
    getUser: async () => ({
      data: { user: { id: "user-1" } },
      error: null,
    }),
  },
} as const;

/**
 * Mock Supabase client for unauthenticated users.
 */
export const MOCK_SUPABASE_UNAUTHENTICATED = {
  auth: {
    getUser: async () => ({
      data: { user: null },
      error: { message: "Unauthorized" },
    }),
  },
} as const;

/**
 * Hoisted mocks for shared use across tests.
 */
export const CALENDAR_MOCKS = {
  createEvent: vi.hoisted(() => vi.fn()),
  createServerSupabase: vi.hoisted(() => vi.fn()),
  deleteEvent: vi.hoisted(() => vi.fn()),
  getServerEnvVarWithFallback: vi.hoisted(() => vi.fn()),
  hasGoogleCalendarScopes: vi.hoisted(() => vi.fn()),
  limitSpy: vi.hoisted(() => vi.fn()),
  listCalendars: vi.hoisted(() => vi.fn()),
  listEvents: vi.hoisted(() => vi.fn()),
  queryFreeBusy: vi.hoisted(() => vi.fn()),
  updateEvent: vi.hoisted(() => vi.fn()),
} as const;

/**
 * Setup shared mocks for calendar routes.
 *
 * @param overrides - Optional overrides for specific mocks
 */
export function setupCalendarMocks(overrides?: {
  authenticated?: boolean;
  rateLimit?: typeof MOCK_RATE_LIMIT_SUCCESS;
  calendars?: unknown;
  events?: unknown;
  hasScopes?: boolean;
}) {
  const isAuthenticated = overrides?.authenticated ?? true;
  const rateLimit = overrides?.rateLimit ?? MOCK_RATE_LIMIT_SUCCESS;
  const hasScopes = overrides?.hasScopes ?? true;

  // Reset all mocks
  Object.values(CALENDAR_MOCKS).forEach((mock) => {
    if (typeof mock === "function" && "mockReset" in mock) {
      mock.mockReset();
    }
  });

  // Setup Supabase mock
  CALENDAR_MOCKS.createServerSupabase.mockResolvedValue(
    isAuthenticated ? MOCK_SUPABASE_AUTHENTICATED : MOCK_SUPABASE_UNAUTHENTICATED
  );

  // Setup Google Calendar mocks
  CALENDAR_MOCKS.listCalendars.mockResolvedValue(
    overrides?.calendars || {
      items: [
        {
          accessRole: "owner",
          id: "primary",
          primary: true,
          summary: "Primary Calendar",
          timeZone: "UTC",
        },
      ],
      kind: "calendar#calendarList",
    }
  );

  CALENDAR_MOCKS.listEvents.mockResolvedValue(
    overrides?.events || {
      items: [
        {
          end: { dateTime: new Date().toISOString() },
          id: "event-1",
          start: { dateTime: new Date().toISOString() },
          summary: "Test Event",
        },
      ],
      kind: "calendar#events",
    }
  );

  CALENDAR_MOCKS.createEvent.mockResolvedValue({
    htmlLink: "https://calendar.google.com/event?eid=xyz",
    id: "event-new",
    summary: "New Event",
  });

  CALENDAR_MOCKS.updateEvent.mockResolvedValue({
    id: "event-1",
    summary: "Updated Event",
  });

  CALENDAR_MOCKS.deleteEvent.mockResolvedValue(undefined);

  CALENDAR_MOCKS.queryFreeBusy.mockResolvedValue({
    calendars: {
      primary: {
        busy: [
          {
            end: "2025-01-15T11:00:00Z",
            start: "2025-01-15T10:00:00Z",
          },
        ],
      },
    },
    kind: "calendar#freeBusy",
    timeMax: new Date("2025-01-16T00:00:00Z"),
    timeMin: new Date("2025-01-15T00:00:00Z"),
  });

  CALENDAR_MOCKS.hasGoogleCalendarScopes.mockResolvedValue(hasScopes);

  // Setup rate limit mock
  CALENDAR_MOCKS.limitSpy.mockResolvedValue(rateLimit);

  // Setup env mock
  CALENDAR_MOCKS.getServerEnvVarWithFallback.mockImplementation((key: string) => {
    if (key === "UPSTASH_REDIS_REST_URL" || key === "UPSTASH_REDIS_REST_TOKEN") {
      return "test-value";
    }
    return undefined;
  });

  // Apply vi.doMock calls
  vi.doMock("@/lib/supabase/server", () => ({
    createServerSupabase: CALENDAR_MOCKS.createServerSupabase,
  }));

  vi.doMock("@/lib/calendar/google", () => ({
    createEvent: CALENDAR_MOCKS.createEvent,
    deleteEvent: CALENDAR_MOCKS.deleteEvent,
    listCalendars: CALENDAR_MOCKS.listCalendars,
    listEvents: CALENDAR_MOCKS.listEvents,
    queryFreeBusy: CALENDAR_MOCKS.queryFreeBusy,
    updateEvent: CALENDAR_MOCKS.updateEvent,
  }));

  vi.doMock("@/lib/calendar/auth", () => ({
    hasGoogleCalendarScopes: CALENDAR_MOCKS.hasGoogleCalendarScopes,
  }));

  vi.doMock("@upstash/ratelimit", () => {
    const slidingWindow = vi.fn(() => ({}));
    const ctor = vi.fn(function RatelimitMock() {
      return {
        limit: CALENDAR_MOCKS.limitSpy,
      };
    }) as unknown as {
      new (...args: unknown[]): { limit: ReturnType<typeof vi.fn> };
      slidingWindow: typeof slidingWindow;
    };
    ctor.slidingWindow = slidingWindow;
    return { Ratelimit: ctor };
  });

  vi.doMock("@upstash/redis", () => ({
    Redis: {
      fromEnv: vi.fn(() => ({})),
    },
  }));

  vi.doMock("@/lib/env/server", () => ({
    getServerEnvVarWithFallback: CALENDAR_MOCKS.getServerEnvVarWithFallback,
  }));
}

/**
 * Build a mock NextRequest for testing.
 *
 * @param url - Request URL
 * @param options - Request options
 * @returns Mock NextRequest
 */
export function buildMockRequest(
  url: string,
  options: {
    method?: string;
    body?: unknown;
    headers?: Record<string, string>;
  } = {}
): NextRequest {
  const { method = "GET", body, headers = {} } = options;
  const request = new Request(url, {
    body: body ? JSON.stringify(body) : undefined,
    headers: { "content-type": "application/json", ...headers },
    method,
  });

  return request as unknown as NextRequest;
}
