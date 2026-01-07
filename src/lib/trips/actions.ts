/**
 * @fileoverview Trips domain server actions (CRUD, collaboration, itinerary, saved places).
 */

"use server";

import "server-only";

import type { SavedPlaceSnapshot } from "@schemas/places";
import type {
  ItineraryItem,
  TripCollaborator,
  TripFilters,
  UiTrip,
} from "@schemas/trips";
import type { Result, ResultError } from "@/lib/result";
import {
  addCollaboratorImpl,
  getTripCollaboratorsImpl,
  removeCollaboratorImpl,
  updateCollaboratorRoleImpl,
} from "./actions/collaborators";
import {
  deleteItineraryItemImpl,
  getTripItineraryImpl,
  upsertItineraryItemImpl,
} from "./actions/itinerary";
import {
  listSavedPlacesImpl,
  removePlaceImpl,
  savePlaceImpl,
} from "./actions/saved-places";
import {
  createTripImpl,
  deleteTripImpl,
  getTripByIdImpl,
  getTripsForUserImpl,
  updateTripImpl,
} from "./actions/trips";

export async function getTripsForUser(
  filters?: TripFilters
): Promise<Result<UiTrip[], ResultError>> {
  return await getTripsForUserImpl(filters);
}

export async function getTripById(
  tripId: number
): Promise<Result<UiTrip, ResultError>> {
  return await getTripByIdImpl(tripId);
}

export async function createTrip(input: unknown): Promise<Result<UiTrip, ResultError>> {
  return await createTripImpl(input);
}

export async function updateTrip(
  tripId: number,
  patch: unknown
): Promise<Result<UiTrip, ResultError>> {
  return await updateTripImpl(tripId, patch);
}

export async function deleteTrip(
  tripId: number
): Promise<Result<{ deleted: true }, ResultError>> {
  return await deleteTripImpl(tripId);
}

export async function getTripCollaborators(tripId: number): Promise<
  Result<
    {
      collaborators: TripCollaborator[];
      isOwner: boolean;
      ownerId: string;
      tripId: number;
    },
    ResultError
  >
> {
  return await getTripCollaboratorsImpl(tripId);
}

export async function addCollaborator(
  tripId: number,
  input: unknown
): Promise<Result<{ collaborator: TripCollaborator; invited: boolean }, ResultError>> {
  return await addCollaboratorImpl(tripId, input);
}

export async function removeCollaborator(
  tripId: number,
  collaboratorUserId: string
): Promise<Result<{ removed: true }, ResultError>> {
  return await removeCollaboratorImpl(tripId, collaboratorUserId);
}

export async function updateCollaboratorRole(
  tripId: number,
  collaboratorUserId: string,
  input: unknown
): Promise<Result<{ collaborator: TripCollaborator }, ResultError>> {
  return await updateCollaboratorRoleImpl(tripId, collaboratorUserId, input);
}

export async function getTripItinerary(
  tripId: number
): Promise<Result<ItineraryItem[], ResultError>> {
  return await getTripItineraryImpl(tripId);
}

export async function upsertItineraryItem(
  tripId: number,
  input: unknown
): Promise<Result<ItineraryItem, ResultError>> {
  return await upsertItineraryItemImpl(tripId, input);
}

export async function deleteItineraryItem(
  tripId: number,
  itemId: number
): Promise<Result<{ deleted: true }, ResultError>> {
  return await deleteItineraryItemImpl(tripId, itemId);
}

export async function listSavedPlaces(
  tripId: number
): Promise<Result<SavedPlaceSnapshot[], ResultError>> {
  return await listSavedPlacesImpl(tripId);
}

export async function savePlace(
  tripId: number,
  snapshot: unknown
): Promise<Result<SavedPlaceSnapshot, ResultError>> {
  return await savePlaceImpl(tripId, snapshot);
}

export async function removePlace(
  tripId: number,
  placeId: string
): Promise<Result<{ deleted: true }, ResultError>> {
  return await removePlaceImpl(tripId, placeId);
}
