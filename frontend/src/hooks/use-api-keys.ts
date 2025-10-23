"use client";

import { useEffect } from "react";
import {
  useApiDeleteMutation,
  useApiMutation,
  useApiQuery,
} from "@/hooks/use-api-query";
import { queryKeys } from "@/lib/query-keys";
import { useApiKeyStore } from "@/stores/api-key-store";
import type {
  AddKeyRequest,
  AddKeyResponse,
  AllKeysResponse,
  DeleteKeyResponse,
  ValidateKeyResponse,
} from "@/types/api-keys";

/**
 * Hook for fetching all user API keys with enhanced caching and error handling
 */
export function useApiKeys() {
  const { setKeys, setSupportedServices } = useApiKeyStore();

  const query = useApiQuery<AllKeysResponse>("/api/user/keys", undefined, {
    queryKey: queryKeys.auth.apiKeys(),
    staleTime: 5 * 60 * 1000, // 5 minutes - API keys don't change often
    gcTime: 15 * 60 * 1000, // 15 minutes cache retention
    retry: (failureCount, error) => {
      // Don't retry auth errors
      if ("status" in error && error.status === 401) return false;
      return failureCount < 2;
    },
  });

  useEffect(() => {
    if (query.data) {
      setKeys(query.data.keys);
      setSupportedServices(query.data.supported_services);
    }
  }, [query.data, setKeys, setSupportedServices]);

  return query;
}

/**
 * Hook for adding a new API key with optimistic updates
 */
export function useAddApiKey() {
  const { updateKey } = useApiKeyStore();

  const mutation = useApiMutation<AddKeyResponse, AddKeyRequest>("/api/user/keys", {
    invalidateQueries: [[...queryKeys.auth.apiKeys()]],
    onSuccess: (data) => {
      updateKey(data.service, {
        is_valid: data.is_valid,
        has_key: true,
        service: data.service,
        last_validated: new Date().toISOString(),
      });
    },
    // Retry on server errors but not on validation errors
    retry: (failureCount, error) => {
      if ("status" in error && error.status === 422) return false; // Validation error
      if ("status" in error && error.status === 401) return false; // Auth error
      return failureCount < 1;
    },
  });

  return mutation;
}

/**
 * Hook for validating an API key without saving it
 */
export function useValidateApiKey() {
  return useApiMutation<ValidateKeyResponse, AddKeyRequest>("/api/user/keys/validate", {
    retry: (_failureCount, _error) => {
      // Don't retry validation calls - they should be immediate
      return false;
    },
  });
}

/**
 * Hook for deleting an API key with optimistic updates
 */
export function useDeleteApiKey() {
  const { removeKey } = useApiKeyStore();

  const mutation = useApiDeleteMutation<DeleteKeyResponse, string>("/api/user/keys", {
    invalidateQueries: [[...queryKeys.auth.apiKeys()]],
    optimisticUpdate: {
      queryKey: [...queryKeys.auth.apiKeys()],
      updater: (oldData: unknown, serviceToDelete: string) => {
        const data = oldData as AllKeysResponse | undefined;
        if (!data) return data;
        const { [serviceToDelete]: deletedKey, ...remainingKeys } = data.keys;
        return {
          ...data,
          keys: remainingKeys,
        };
      },
    },
    onSuccess: (data) => {
      if (data?.success) {
        removeKey(data.service);
      }
    },
    retry: (failureCount, error) => {
      if ("status" in error && error.status === 404) return false; // Not found
      if ("status" in error && error.status === 401) return false; // Auth error
      return failureCount < 1;
    },
  });

  return mutation;
}
