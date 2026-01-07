/**
 * @fileoverview React Query hooks for trip collaborator management.
 */

"use client";

import type {
  TripCollaborator,
  TripCollaboratorInviteInput,
  TripCollaboratorRole,
  TripCollaboratorRoleUpdateInput,
} from "@schemas/trips";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCurrentUserId } from "@/hooks/use-current-user-id";
import { ApiError, type ApiErrorCode, type AppError } from "@/lib/api/error-types";
import { keys } from "@/lib/keys";
import { cacheTimes, staleTimes } from "@/lib/query/config";
import type { Result, ResultError } from "@/lib/result";
import {
  addCollaborator,
  getTripCollaborators,
  removeCollaborator,
  updateCollaboratorRole,
} from "@/lib/trips/actions";

export type TripCollaboratorsResponse = {
  readonly tripId: number;
  readonly ownerId: string;
  readonly isOwner: boolean;
  readonly collaborators: TripCollaborator[];
};

export type InviteTripCollaboratorResponse = {
  readonly invited: boolean;
  readonly collaborator: TripCollaborator;
};

export type UpdateTripCollaboratorRoleResponse = {
  readonly collaborator: TripCollaborator;
};

function statusFromResultErrorCode(code: string): number {
  switch (code) {
    case "unauthorized":
      return 401;
    case "forbidden":
      return 403;
    case "not_found":
      return 404;
    case "conflict":
      return 409;
    case "invalid_request":
      return 422;
    case "rate_limited":
      return 429;
    case "server_error":
      return 500;
    default:
      return 500;
  }
}

function apiCodeFromStatus(status: number): ApiErrorCode {
  if (status === 409) return "HTTP_409";
  if (status === 400) return "HTTP_400";
  if (status === 422) return "HTTP_422";
  return ApiError.codeFromStatus(status);
}

function toApiError(error: ResultError, endpoint: string): ApiError {
  const status = statusFromResultErrorCode(error.error);
  return new ApiError({
    code: apiCodeFromStatus(status),
    data: { error: error.error, issues: error.issues },
    endpoint,
    fieldErrors: error.fieldErrors,
    message: error.reason,
    status,
  });
}

function unwrapResult<T>(result: Result<T, ResultError>, endpoint: string): T {
  if (result.ok) return result.data;
  throw toApiError(result.error, endpoint);
}

export function useTripCollaborators(
  tripId: number | null,
  options?: { userId?: string | null }
) {
  const inferredUserId = useCurrentUserId();
  const userId = options?.userId ?? inferredUserId;
  const enabled = tripId !== null && !!userId;

  return useQuery<TripCollaboratorsResponse, AppError>({
    enabled,
    gcTime: cacheTimes.medium,
    queryFn: async () => {
      // Invariant: queryFn should only run when `enabled` is true
      if (tripId === null) {
        throw new Error("Trip id is required");
      }

      const result = await getTripCollaborators(tripId);
      return unwrapResult(result, "trips.collaborators.list");
    },
    queryKey:
      tripId === null || !userId
        ? keys.trips.collaboratorsDisabled()
        : keys.trips.collaborators(userId, tripId),
    staleTime: staleTimes.realtime,
    throwOnError: false,
  });
}

export function useInviteTripCollaborator(tripId: number) {
  const queryClient = useQueryClient();
  const userId = useCurrentUserId();

  return useMutation<
    InviteTripCollaboratorResponse,
    AppError,
    TripCollaboratorInviteInput
  >({
    mutationFn: async (payload) => {
      const result = await addCollaborator(tripId, payload);
      return unwrapResult(result, "trips.collaborators.add");
    },
    onSuccess: () => {
      if (userId) {
        queryClient.invalidateQueries({
          queryKey: keys.trips.collaborators(userId, tripId),
        });
        queryClient.invalidateQueries({ queryKey: keys.trips.user(userId) });
        return;
      }

      queryClient.invalidateQueries({ queryKey: keys.trips.all() });
    },
    throwOnError: false,
  });
}

export function useUpdateTripCollaboratorRole(tripId: number) {
  const queryClient = useQueryClient();
  const userId = useCurrentUserId();

  return useMutation<
    UpdateTripCollaboratorRoleResponse,
    AppError,
    { collaboratorUserId: string; payload: TripCollaboratorRoleUpdateInput }
  >({
    mutationFn: async ({ collaboratorUserId, payload }) => {
      const result = await updateCollaboratorRole(tripId, collaboratorUserId, payload);
      return unwrapResult(result, "trips.collaborators.update_role");
    },
    onSuccess: () => {
      if (userId) {
        queryClient.invalidateQueries({
          queryKey: keys.trips.collaborators(userId, tripId),
        });
        queryClient.invalidateQueries({ queryKey: keys.trips.user(userId) });
        return;
      }

      queryClient.invalidateQueries({ queryKey: keys.trips.all() });
    },
    throwOnError: false,
  });
}

export function useRemoveTripCollaborator(tripId: number) {
  const queryClient = useQueryClient();
  const userId = useCurrentUserId();

  return useMutation<void, AppError, { collaboratorUserId: string }>({
    mutationFn: async ({ collaboratorUserId }) => {
      const result = await removeCollaborator(tripId, collaboratorUserId);
      unwrapResult(result, "trips.collaborators.remove");
    },
    onSuccess: () => {
      if (userId) {
        queryClient.invalidateQueries({
          queryKey: keys.trips.collaborators(userId, tripId),
        });
        queryClient.invalidateQueries({ queryKey: keys.trips.user(userId) });
        return;
      }

      queryClient.invalidateQueries({ queryKey: keys.trips.all() });
    },
    throwOnError: false,
  });
}

export function getTripEditPermission(params: {
  currentUserId: string | null;
  ownerId: string;
  collaborators: TripCollaborator[];
}): { canEdit: boolean; role: TripCollaboratorRole | "unknown" } {
  if (!params.currentUserId) {
    return { canEdit: false, role: "unknown" };
  }

  if (params.currentUserId === params.ownerId) {
    return { canEdit: true, role: "owner" };
  }

  const self = params.collaborators.find((c) => c.userId === params.currentUserId);
  const role: TripCollaboratorRole | "unknown" = self?.role ?? "unknown";
  const canEdit = role === "owner" || role === "editor";
  return { canEdit, role };
}
