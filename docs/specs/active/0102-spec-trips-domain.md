# SPEC-0102: Trips domain (CRUD, itinerary, collaboration)

**Version**: 1.2.0
**Status**: Final
**Date**: 2026-07-09

## Goals

- Users can create and manage trips.
- Trips support collaborators with roles.
- Trips contain itinerary items, notes, and derived AI suggestions.

## Core entities

- trip
  - id, owner_id, name, destination, date_range, preferences, created_at, updated_at
- trip_member
  - trip_id, user_id, role (owner, editor, viewer)
- itinerary_item
  - trip_id, type (activity, meal, transport, accommodation, event, other)
  - start_at, end_at
  - structured payload JSONB per type
- trip_chat_session
  - trip_id, chat_id (optional linkage to chat)

## UI requirements

- Trips list page (server shell + hydrated client list)
- Trip detail page:
  - itinerary timeline
  - “ask TripSage” chat entrypoint
  - collaborator management

## API / Actions

Server Actions:

- createTrip(input)
- updateTrip(id, patch)
- deleteTrip(id)
- addCollaborator(tripId, email, role)
- removeCollaborator(tripId, userId)
- upsertItineraryItem(tripId, item)
- deleteItineraryItem(tripId, itemId)

Queries:

- getTripsForUser(userId)
- getTripById(userId, tripId) with membership validation

Security and authorization:

- Enforce trip access at the database layer (RLS) and at the API boundary (server actions/queries must validate membership).
- Mutations must verify the caller is an owner/editor as required (e.g., collaborator changes, itinerary edits).
- Disallow edge cases like removing the last remaining owner.

Validation:

- Zod schemas for all inputs and patches
- Strict enums for itinerary item types (see `src/domain/schemas/trips.ts` `itineraryItemTypeSchema`).
  - Allowed values: `activity`, `meal`, `transport`, `accommodation`, `event`, `other`
- Date inputs:
  - User-facing trip date fields accept either:
    - date-only (`YYYY-MM-DD`)
    - ISO 8601 datetime strings (timezone-aware)
  - Actions normalize to the canonical storage format expected by Supabase/Postgres; timestamp fields remain `TIMESTAMPTZ` ISO strings.

Error handling:

- Prefer domain-specific error classes where available; map to standardized error codes/messages at the boundary.
- Server actions should surface errors with stable error identifiers that the UI can render without string matching.

Activation measurement:

- Emit `activation.trip_created` only after the trip insert succeeds and the returned
  trip passes database and UI validation.
- Emit `activation.itinerary_item_completed` only after an itinerary-item insert or
  update succeeds and the validated returned `bookingStatus` is `completed`.
- Activation telemetry is best effort and cannot change a successful persisted action
  result. Events contain only low-cardinality operation/item-type attributes and
  optional keyed-hash pseudonyms. Do not emit raw identifiers or trip/itinerary content.
- An activated planner is one unique `user.id_hash` with a
  `activation.trip_created` event. Itinerary completion is the deeper conversion
  milestone.
- Monetization remains disabled until production evidence includes at least 500
  activated planners and 30 explicit paid-feature requests, counted once per requester
  who names a paid capability or states a willingness to pay.
- Production aggregation requires an OpenTelemetry trace drain/exporter. The live
  Vercel environment does not configure one, so the thresholds cannot yet be evaluated.

Testing

- Unit tests for schemas and actions.
- E2E: create trip, add itinerary item, invite collaborator (mock email).
- Add scenarios:
  - Unauthorized access attempts (read and write)
  - Removing the last owner is rejected
  - Concurrent edits by multiple collaborators (last-write-wins or conflict strategy as implemented)

## Post-acceptance updates (2026-01-19)

- Fixed schema correctness issues discovered during an end-to-end Trips create-flow validation:
  - Postgres/Supabase timestamps serialize with timezone offsets; runtime validation now accepts offsets (`primitiveSchemas.isoDateTime` uses `z.iso.datetime({ offset: true })`).
  - Supabase `trips` JSON columns `flexibility` and `search_metadata` are treated as nullable to match the generated database types (`Json | null`).
- Verified the dashboard trip creation flow end-to-end with `agent-browser`:
  - create trip in UI
  - confirm success toast
  - navigate to trip detail page.
