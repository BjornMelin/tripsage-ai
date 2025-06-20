"use client";

import type { ApiError } from "@/lib/api/client";
import {
  type UseMutationOptions,
  type UseQueryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { z } from "zod";
import { useAuthenticatedApi } from "./use-authenticated-api";

// Zod schemas for validation
const ApiQueryParamsSchema = z
  .record(z.union([z.string(), z.number(), z.boolean()]))
  .optional();

const EndpointSchema = z.string().min(1, "Endpoint cannot be empty");

const _HttpMethodSchema = z.enum(["GET", "POST", "PUT", "PATCH", "DELETE"]);

type ApiQueryOptions<TData, TError> = Omit<
  UseQueryOptions<TData, TError, TData, (string | Record<string, unknown>)[]>,
  "queryKey" | "queryFn"
>;

type ApiMutationOptions<TData, TVariables, TError> = Omit<
  UseMutationOptions<TData, TError, TVariables, unknown>,
  "mutationFn"
>;

// Hook for GET requests
export function useApiQuery<TData = any, TError = ApiError>(
  endpoint: string,
  params?: Record<string, unknown>,
  options?: ApiQueryOptions<TData, TError>
) {
  // Validate inputs with Zod
  const validatedEndpoint = EndpointSchema.parse(endpoint);
  const validatedParams = ApiQueryParamsSchema.parse(params);

  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useQuery<TData, TError, TData, (string | Record<string, unknown>)[]>({
    queryKey: [
      validatedEndpoint,
      ...(validatedParams ? [validatedParams as Record<string, unknown>] : []),
    ],
    queryFn: () =>
      makeAuthenticatedRequest<TData>(validatedEndpoint, { params: validatedParams }),
    ...options,
  });
}

// Hook for POST requests
export function useApiMutation<
  TData = unknown,
  TVariables = unknown,
  TError = ApiError,
>(endpoint: string, options?: ApiMutationOptions<TData, TVariables, TError>) {
  const _queryClient = useQueryClient();
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useMutation<TData, TError, TVariables, unknown>({
    mutationFn: (variables) =>
      makeAuthenticatedRequest<TData>(endpoint, {
        method: "POST",
        body: JSON.stringify(variables),
        headers: { "Content-Type": "application/json" },
      }),
    // Remove onSuccess - let consumers handle it with useEffect
    ...options,
  });
}

// Hook for PUT requests
export function useApiPutMutation<TData = any, TVariables = any, TError = ApiError>(
  endpoint: string,
  options?: ApiMutationOptions<TData, TVariables, TError>
) {
  const _queryClient = useQueryClient();
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useMutation<TData, TError, TVariables, unknown>({
    mutationFn: (variables) =>
      makeAuthenticatedRequest<TData>(endpoint, {
        method: "PUT",
        body: JSON.stringify(variables),
        headers: { "Content-Type": "application/json" },
      }),
    // Remove onSuccess - let consumers handle it with useEffect
    ...options,
  });
}

// Hook for PATCH requests
export function useApiPatchMutation<TData = any, TVariables = any, TError = ApiError>(
  endpoint: string,
  options?: ApiMutationOptions<TData, TVariables, TError>
) {
  const _queryClient = useQueryClient();
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useMutation<TData, TError, TVariables, unknown>({
    mutationFn: (variables) =>
      makeAuthenticatedRequest<TData>(endpoint, {
        method: "PATCH",
        body: JSON.stringify(variables),
        headers: { "Content-Type": "application/json" },
      }),
    // Remove onSuccess - let consumers handle it with useEffect
    ...options,
  });
}

// Hook for DELETE requests
export function useApiDeleteMutation<TData = any, TVariables = any, TError = ApiError>(
  endpoint: string,
  options?: ApiMutationOptions<TData, TVariables, TError>
) {
  const _queryClient = useQueryClient();
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useMutation<TData, TError, TVariables, unknown>({
    mutationFn: (variables) =>
      makeAuthenticatedRequest<TData>(`${endpoint}/${variables}`, {
        method: "DELETE",
      }),
    // Remove onSuccess - let consumers handle it with useEffect
    ...options,
  });
}
