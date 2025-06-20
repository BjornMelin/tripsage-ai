"use client";

import { type AppError, handleApiError } from "@/lib/api/error-types";
import { queryKeys } from "@/lib/query-keys";
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

const HttpMethodSchema = z.enum(["GET", "POST", "PUT", "PATCH", "DELETE"]);

// Enhanced type definitions with proper generics
type ApiQueryOptions<TData, TError = AppError> = Omit<
  UseQueryOptions<TData, TError, TData, readonly unknown[]>,
  "queryKey" | "queryFn"
> & {
  queryKey?: readonly unknown[];
};

type ApiMutationOptions<TData, TVariables, TError = AppError> = Omit<
  UseMutationOptions<TData, TError, TVariables, unknown>,
  "mutationFn"
> & {
  invalidateQueries?: readonly unknown[][];
  optimisticUpdate?: {
    queryKey: readonly unknown[];
    updater: (old: unknown, variables: TVariables) => unknown;
  };
};

interface MutationContext<TVariables = unknown> {
  previousData?: unknown;
  optimisticData?: unknown;
  variables?: TVariables;
}

// Hook for GET requests with enhanced error handling and TypeScript
export function useApiQuery<TData = unknown, TError = AppError>(
  endpoint: string,
  params?: Record<string, unknown>,
  options?: ApiQueryOptions<TData, TError>
) {
  // Validate inputs with Zod
  const validatedEndpoint = EndpointSchema.parse(endpoint);
  const validatedParams = ApiQueryParamsSchema.parse(params);

  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  // Use provided queryKey or generate default
  const queryKey = options?.queryKey || [
    validatedEndpoint,
    ...(validatedParams ? [validatedParams] : []),
  ];

  return useQuery<TData, TError, TData, readonly unknown[]>({
    queryKey,
    queryFn: async () => {
      try {
        return await makeAuthenticatedRequest<TData>(validatedEndpoint, {
          params: validatedParams,
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    throwOnError: false, // Let components handle errors
    ...options,
  });
}

// Hook for POST requests with optimistic updates and proper error handling
export function useApiMutation<
  TData = unknown,
  TVariables = unknown,
  TError = AppError,
>(endpoint: string, options?: ApiMutationOptions<TData, TVariables, TError>) {
  const queryClient = useQueryClient();
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useMutation<TData, TError, TVariables, MutationContext<TVariables>>({
    mutationFn: async (variables) => {
      try {
        return await makeAuthenticatedRequest<TData>(endpoint, {
          method: "POST",
          body: JSON.stringify(variables),
          headers: { "Content-Type": "application/json" },
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onMutate: async (variables) => {
      const context: MutationContext<TVariables> = { variables };

      // Handle optimistic updates
      if (options?.optimisticUpdate) {
        const { queryKey, updater } = options.optimisticUpdate;

        // Cancel outgoing refetches
        await queryClient.cancelQueries({ queryKey });

        // Snapshot previous value
        context.previousData = queryClient.getQueryData(queryKey);

        // Optimistically update cache
        const optimisticData = updater(context.previousData, variables);
        queryClient.setQueryData(queryKey, optimisticData);
        context.optimisticData = optimisticData;
      }

      // Call user-defined onMutate
      if (options?.onMutate) {
        const userContext = await options.onMutate(variables);
        Object.assign(context, userContext);
      }

      return context;
    },
    onError: (error, variables, context) => {
      // Rollback optimistic updates
      if (context?.previousData && options?.optimisticUpdate) {
        queryClient.setQueryData(
          options.optimisticUpdate.queryKey,
          context.previousData
        );
      }

      // Call user-defined onError
      options?.onError?.(error, variables, context);
    },
    onSuccess: (data, variables, context) => {
      // Invalidate specified queries
      if (options?.invalidateQueries) {
        options.invalidateQueries.forEach((queryKey) => {
          queryClient.invalidateQueries({ queryKey });
        });
      }

      // Call user-defined onSuccess
      options?.onSuccess?.(data, variables, context);
    },
    onSettled: (data, error, variables, context) => {
      // Refetch optimistic update query on settle
      if (options?.optimisticUpdate) {
        queryClient.invalidateQueries({ queryKey: options.optimisticUpdate.queryKey });
      }

      // Call user-defined onSettled
      options?.onSettled?.(data, error, variables, context);
    },
    throwOnError: false, // Let components handle errors
    // Exclude our custom options from the base mutation options
    ...Object.fromEntries(
      Object.entries(options || {}).filter(
        ([key]) => !["invalidateQueries", "optimisticUpdate"].includes(key)
      )
    ),
  });
}

// Hook for PUT requests
export function useApiPutMutation<
  TData = unknown,
  TVariables = unknown,
  TError = AppError,
>(endpoint: string, options?: ApiMutationOptions<TData, TVariables, TError>) {
  return useApiMutationWithMethod("PUT", endpoint, options);
}

// Hook for PATCH requests
export function useApiPatchMutation<
  TData = unknown,
  TVariables = unknown,
  TError = AppError,
>(endpoint: string, options?: ApiMutationOptions<TData, TVariables, TError>) {
  return useApiMutationWithMethod("PATCH", endpoint, options);
}

// Hook for DELETE requests
export function useApiDeleteMutation<
  TData = unknown,
  TVariables = unknown,
  TError = AppError,
>(endpoint: string, options?: ApiMutationOptions<TData, TVariables, TError>) {
  const queryClient = useQueryClient();
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useMutation<TData, TError, TVariables, MutationContext<TVariables>>({
    mutationFn: async (variables) => {
      try {
        // Handle both string variables (ID) and object variables
        const deleteEndpoint =
          typeof variables === "string" || typeof variables === "number"
            ? `${endpoint}/${variables}`
            : endpoint;

        return await makeAuthenticatedRequest<TData>(deleteEndpoint, {
          method: "DELETE",
          ...(typeof variables === "object" &&
            variables !== null && {
              body: JSON.stringify(variables),
              headers: { "Content-Type": "application/json" },
            }),
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onMutate: async (variables) => {
      const context: MutationContext<TVariables> = { variables };

      // Handle optimistic updates
      if (options?.optimisticUpdate) {
        const { queryKey, updater } = options.optimisticUpdate;

        await queryClient.cancelQueries({ queryKey });
        context.previousData = queryClient.getQueryData(queryKey);

        const optimisticData = updater(context.previousData, variables);
        queryClient.setQueryData(queryKey, optimisticData);
        context.optimisticData = optimisticData;
      }

      if (options?.onMutate) {
        const userContext = await options.onMutate(variables);
        Object.assign(context, userContext);
      }

      return context;
    },
    onError: (error, variables, context) => {
      if (context?.previousData && options?.optimisticUpdate) {
        queryClient.setQueryData(
          options.optimisticUpdate.queryKey,
          context.previousData
        );
      }
      options?.onError?.(error, variables, context);
    },
    onSuccess: (data, variables, context) => {
      if (options?.invalidateQueries) {
        options.invalidateQueries.forEach((queryKey) => {
          queryClient.invalidateQueries({ queryKey });
        });
      }
      options?.onSuccess?.(data, variables, context);
    },
    onSettled: (data, error, variables, context) => {
      if (options?.optimisticUpdate) {
        queryClient.invalidateQueries({ queryKey: options.optimisticUpdate.queryKey });
      }
      options?.onSettled?.(data, error, variables, context);
    },
    throwOnError: false,
    ...Object.fromEntries(
      Object.entries(options || {}).filter(
        ([key]) => !["invalidateQueries", "optimisticUpdate"].includes(key)
      )
    ),
  });
}

// Helper function for PUT/PATCH mutations
function useApiMutationWithMethod<
  TData = unknown,
  TVariables = unknown,
  TError = AppError,
>(
  method: "PUT" | "PATCH",
  endpoint: string,
  options?: ApiMutationOptions<TData, TVariables, TError>
) {
  const queryClient = useQueryClient();
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useMutation<TData, TError, TVariables, MutationContext<TVariables>>({
    mutationFn: async (variables) => {
      try {
        return await makeAuthenticatedRequest<TData>(endpoint, {
          method,
          body: JSON.stringify(variables),
          headers: { "Content-Type": "application/json" },
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onMutate: async (variables) => {
      const context: MutationContext<TVariables> = { variables };

      if (options?.optimisticUpdate) {
        const { queryKey, updater } = options.optimisticUpdate;

        await queryClient.cancelQueries({ queryKey });
        context.previousData = queryClient.getQueryData(queryKey);

        const optimisticData = updater(context.previousData, variables);
        queryClient.setQueryData(queryKey, optimisticData);
        context.optimisticData = optimisticData;
      }

      if (options?.onMutate) {
        const userContext = await options.onMutate(variables);
        Object.assign(context, userContext);
      }

      return context;
    },
    onError: (error, variables, context) => {
      if (context?.previousData && options?.optimisticUpdate) {
        queryClient.setQueryData(
          options.optimisticUpdate.queryKey,
          context.previousData
        );
      }
      options?.onError?.(error, variables, context);
    },
    onSuccess: (data, variables, context) => {
      if (options?.invalidateQueries) {
        options.invalidateQueries.forEach((queryKey) => {
          queryClient.invalidateQueries({ queryKey });
        });
      }
      options?.onSuccess?.(data, variables, context);
    },
    onSettled: (data, error, variables, context) => {
      if (options?.optimisticUpdate) {
        queryClient.invalidateQueries({ queryKey: options.optimisticUpdate.queryKey });
      }
      options?.onSettled?.(data, error, variables, context);
    },
    throwOnError: false,
    ...Object.fromEntries(
      Object.entries(options || {}).filter(
        ([key]) => !["invalidateQueries", "optimisticUpdate"].includes(key)
      )
    ),
  });
}
