# SPEC-0102: Trips domain (CRUD, itinerary, collaboration)

**Version**: 1.0.0  
**Status**: Final  
**Date**: 2026-01-05

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
  - trip_id, type (flight, lodging, activity, transport, note)
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

Validation:

- Zod schemas for all inputs and patches
- Strict enums for itinerary item types

Testing

- Unit tests for schemas and actions.
- E2E: create trip, add itinerary item, invite collaborator (mock email).
