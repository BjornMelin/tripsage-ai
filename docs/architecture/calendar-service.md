# Calendar & Time Service Architecture

## Overview

The calendar and time service provides Google Calendar integration, ICS
import/export, timezone utilities, and AI SDK tools for calendar operations.
All functionality is implemented server-side in Next.js 16 with zero client-side
secrets.

## Architecture Decisions

### Decision Framework Score: 91/100

| Category | Weight | Score | Rationale |
|----------|--------|-------|-----------|
| Solution Leverage | 35% | 34/35 | Google REST + minimal libs |
| Application Value | 30% | 27/30 | Read/write, availability, ICS import/export |
| Maintenance Load | 25% | 22/25 | Thin adapters, server-only, mocks |
| Adaptability | 10% | 8/10 | Provider abstraction for Outlook/Microsoft |

## Components

### Schemas (`src/domain/schemas/`)

- **`calendar.ts`**: Zod v4 schemas aligned with Google Calendar API
  - Event models: `CalendarEvent`, `CreateEventRequest`, `UpdateEventRequest`
  - List models: `CalendarList`, `EventsListRequest`, `EventsListResponse`
  - Free/busy: `FreeBusyRequest`, `FreeBusyResponse`
- **`temporal.ts`**: Temporal schemas for dates, times, durations, recurrence
  - `DateRange`, `TimeRange`, `DateTimeRange`, `Duration`
  - `RecurrenceRule`, `BusinessHours`, `Availability`

### Server Utilities (`src/lib/calendar/`)

- **`auth.ts`**: OAuth token retrieval from Supabase session
  - `getGoogleProviderToken()`: Retrieves Google provider token from session
  - `hasGoogleCalendarScopes()`: Validates required OAuth scopes
- **`google.ts`**: Google Calendar REST API v3 wrapper
  - `listCalendars()`, `getCalendar()`, `listEvents()`, `getEvent()`
  - `createEvent()`, `updateEvent()`, `deleteEvent()`
  - `queryFreeBusy()`: Free/busy availability queries
- **`trip-export.ts`**: Trip-to-calendar conversion utilities
  - `tripToCalendarEvents()`: Converts trip destinations/activities to calendar events
  - `exportTripToICS()`: Exports trip as ICS file

### API Routes (`src/app/api/calendar/`)

All routes are server-only with `dynamic = "force-dynamic"`:

- **`/api/calendar/status`** (GET)
  - Returns connection status and list of calendars
  - Rate limit: 60 req/min
- **`/api/calendar/events`** (GET/POST/PATCH/DELETE)
  - GET: List events with filters (timeMin, timeMax, calendarId, etc.)
  - POST: Create event
  - PATCH: Update event (requires eventId query param)
  - DELETE: Delete event (requires eventId query param)
  - Rate limits: 60 req/min (read), 10 req/min (write)
- **`/api/calendar/freebusy`** (POST)
  - Query free/busy information for calendars
  - Rate limit: 30 req/min
- **`/api/calendar/ics/import`** (POST)
  - Parse ICS file/text into events payload
  - Rate limit: 20 req/min
- **`/api/calendar/ics/export`** (POST)
  - Generate ICS file from events payload
  - Rate limit: 30 req/min

### AI SDK Tools (`src/ai/tools/server/calendar.ts`)

- **`createCalendarEvent`**: Create events in user's Google Calendar
- **`getAvailability`**: Check calendar availability (free/busy)
- **`exportItineraryToICS`**: Export events to ICS format

Tools are automatically available in chat via `toolRegistry` in `src/ai/tools/index.ts`.

### UI Components (`src/components/calendar/`)

- **`CalendarConnect`**: Server component wrapper for connection status
- **`CalendarStatus`**: Server component displaying connection status and calendars
- **`CalendarConnectClient`**: Client component for OAuth connection flow
- **`CalendarEventForm`**: Client component for creating/editing events
- **`CalendarEventList`**: Server component displaying events list

### Pages

- **`/dashboard/calendar`**: Main calendar management page
  - Tabs: Connection, Events, Create Event
  - Integrated with all calendar components

## Authentication & Security

### OAuth Flow

1. User clicks "Connect Google Calendar" in `CalendarConnectClient`
2. Supabase OAuth initiated with scope: `https://www.googleapis.com/auth/calendar.events`
3. Callback handled by `/auth/callback` route
4. Provider token stored in Supabase session

### Token Retrieval

- Server-side only via `getGoogleProviderToken()` in `lib/calendar/auth.ts`
- Token accessed from `session.provider_token` (Supabase OAuth field)
- Automatic refresh handled by Supabase session management

### Rate Limiting

- Per-user rate limits via Upstash Redis
- Limits initialized inside request handlers (not module scope)
- Different limits for read vs write operations

## Libraries

- **`ical-generator`**: Generate ICS files
- **`node-ical`**: Parse ICS files
- **`luxon`**: Timezone handling (via native Intl API)
- **`rrule`**: RFC 5545 recurrence rule parsing (future use)

## Integration Points

### Trip Export

- Trip detail page (`/dashboard/trips/[id]`) includes "Export to Calendar" button
- Converts trip destinations, activities, and transportation to calendar events
- Downloads ICS file for import into any calendar application

### AI Chat Integration

- Calendar tools automatically available in chat via `toolRegistry`
- AI can create events, check availability, and export itineraries
- Tools include proper error handling and user-friendly responses

## Error Handling

- All routes return explicit 4xx on validation errors
- Google API errors wrapped in `GoogleCalendarApiError`
- Token errors return user-friendly messages prompting reconnection
- Rate limit errors include retry headers

## Testing Strategy

- **Unit tests**: Schemas, utilities, conversion functions
- **Integration tests**: Route handlers with mocked Google API and Upstash
- **E2E tests**: Playwright flows for connect/list/create/export

## Future Enhancements

- Microsoft Outlook/Exchange support (provider abstraction ready)
- Recurrence rule expansion and editing
- Calendar sync (bidirectional)
- Event reminders and notifications
- Multi-calendar management UI
