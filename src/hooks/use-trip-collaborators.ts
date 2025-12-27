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
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";
import { type AppError, handleApiError } from "@/lib/api/error-types";
import { cacheTimes, staleTimes } from "@/lib/query/config";
import { queryKeys } from "@/lib/query-keys";

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

export function useTripCollaborators(tripId: number | null) {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useQuery<TripCollaboratorsResponse, AppError>({
    enabled: tripId !== null,
    gcTime: cacheTimes.medium,
    queryFn: async () => {
      // Invariant: queryFn should only run when `enabled` is true
      if (tripId === null) {
        throw new Error("Trip id is required");
      }
      try {
        return await makeAuthenticatedRequest<TripCollaboratorsResponse>(
          `/api/trips/${tripId}/collaborators`
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey:
      tripId === null
        ? queryKeys.trips.collaboratorsDisabled()
        : queryKeys.trips.collaborators(tripId),
    staleTime: staleTimes.realtime,
    throwOnError: false,
  });
}

export function useInviteTripCollaborator(tripId: number) {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();

  return useMutation<
    InviteTripCollaboratorResponse,
    AppError,
    TripCollaboratorInviteInput
  >({
    mutationFn: async (payload) => {
      try {
        return await makeAuthenticatedRequest<InviteTripCollaboratorResponse>(
          `/api/trips/${tripId}/collaborators`,
          {
            body: JSON.stringify(payload),
            headers: { "Content-Type": "application/json" },
            method: "POST",
          }
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.trips.collaborators(tripId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.trips.all() });
    },
    throwOnError: false,
  });
}

export function useUpdateTripCollaboratorRole(tripId: number) {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();

  return useMutation<
    UpdateTripCollaboratorRoleResponse,
    AppError,
    { collaboratorUserId: string; payload: TripCollaboratorRoleUpdateInput }
  >({
    mutationFn: async ({ collaboratorUserId, payload }) => {
      try {
        return await makeAuthenticatedRequest<UpdateTripCollaboratorRoleResponse>(
          `/api/trips/${tripId}/collaborators/${collaboratorUserId}`,
          {
            body: JSON.stringify(payload),
            headers: { "Content-Type": "application/json" },
            method: "PATCH",
          }
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.trips.collaborators(tripId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.trips.all() });
    },
    throwOnError: false,
  });
}

export function useRemoveTripCollaborator(tripId: number) {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();

  return useMutation<void, AppError, { collaboratorUserId: string }>({
    mutationFn: async ({ collaboratorUserId }) => {
      try {
        await makeAuthenticatedRequest(
          `/api/trips/${tripId}/collaborators/${collaboratorUserId}`,
          {
            method: "DELETE",
          }
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.trips.collaborators(tripId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.trips.all() });
    },
    throwOnError: false,
  });
}

export function getTripEditPermission(params: {
  currentUserId: string | null;
  ownerId: string;
  collaborators: TripCollaborator[];
}): { canEdit: boolean; role: "admin" | "editor" | "owner" | "viewer" | "unknown" } {
  if (!params.currentUserId) {
    return { canEdit: false, role: "unknown" };
  }

  if (params.currentUserId === params.ownerId) {
    return { canEdit: true, role: "owner" };
  }

  const self = params.collaborators.find((c) => c.userId === params.currentUserId);
  const role: TripCollaboratorRole | "unknown" = self?.role ?? "unknown";
  const canEdit = role === "admin" || role === "editor";
  return { canEdit, role: role === "unknown" ? "unknown" : role };
}
