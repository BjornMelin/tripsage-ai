"use client";

import { type ApiError, api } from "@/lib/api/client";
import {
  type UseMutationOptions,
  type UseQueryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

type ApiQueryOptions<TData, TError> = Omit<
  UseQueryOptions<TData, TError, TData, string[]>,
  "queryKey" | "queryFn"
>;

type ApiMutationOptions<TData, TVariables, TError> = Omit<
  UseMutationOptions<TData, TError, TVariables, unknown>,
  "mutationFn"
>;

// Hook for GET requests
export function useApiQuery<TData = any, TError = ApiError>(
  endpoint: string,
  params?: Record<string, any>,
  options?: ApiQueryOptions<TData, TError>
) {
  return useQuery<TData, TError, TData, string[]>({
    queryKey: [endpoint, ...(params ? [params] : [])],
    queryFn: () => api.get<TData>(endpoint, { params }),
    ...options,
  });
}

// Hook for POST requests
export function useApiMutation<TData = any, TVariables = any, TError = ApiError>(
  endpoint: string,
  options?: ApiMutationOptions<TData, TVariables, TError>
) {
  const queryClient = useQueryClient();

  return useMutation<TData, TError, TVariables, unknown>({
    mutationFn: (variables) => api.post<TData>(endpoint, variables),
    onSuccess: (data, variables, context) => {
      // Invalidate queries by default - override this in options if needed
      if (options?.onSuccess) {
        options.onSuccess(data, variables, context);
      } else {
        queryClient.invalidateQueries({ queryKey: [endpoint] });
      }
    },
    ...options,
  });
}

// Hook for PUT requests
export function useApiPutMutation<TData = any, TVariables = any, TError = ApiError>(
  endpoint: string,
  options?: ApiMutationOptions<TData, TVariables, TError>
) {
  const queryClient = useQueryClient();

  return useMutation<TData, TError, TVariables, unknown>({
    mutationFn: (variables) => api.put<TData>(endpoint, variables),
    onSuccess: (data, variables, context) => {
      if (options?.onSuccess) {
        options.onSuccess(data, variables, context);
      } else {
        queryClient.invalidateQueries({ queryKey: [endpoint] });
      }
    },
    ...options,
  });
}

// Hook for PATCH requests
export function useApiPatchMutation<TData = any, TVariables = any, TError = ApiError>(
  endpoint: string,
  options?: ApiMutationOptions<TData, TVariables, TError>
) {
  const queryClient = useQueryClient();

  return useMutation<TData, TError, TVariables, unknown>({
    mutationFn: (variables) => api.patch<TData>(endpoint, variables),
    onSuccess: (data, variables, context) => {
      if (options?.onSuccess) {
        options.onSuccess(data, variables, context);
      } else {
        queryClient.invalidateQueries({ queryKey: [endpoint] });
      }
    },
    ...options,
  });
}

// Hook for DELETE requests
export function useApiDeleteMutation<TData = any, TVariables = any, TError = ApiError>(
  endpoint: string,
  options?: ApiMutationOptions<TData, TVariables, TError>
) {
  const queryClient = useQueryClient();

  return useMutation<TData, TError, TVariables, unknown>({
    mutationFn: (variables) => api.delete<TData>(`${endpoint}/${variables}`),
    onSuccess: (data, variables, context) => {
      if (options?.onSuccess) {
        options.onSuccess(data, variables, context);
      } else {
        queryClient.invalidateQueries({ queryKey: [endpoint] });
      }
    },
    ...options,
  });
}
