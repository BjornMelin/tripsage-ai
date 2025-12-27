/**
 * @fileoverview React Query hook for retrieving the current Supabase user id.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { cacheTimes } from "@/lib/query/config";
import { queryKeys } from "@/lib/query-keys";
import { useSupabaseRequired } from "@/lib/supabase";

export function useCurrentUserId(): string | null {
  const supabase = useSupabaseRequired();

  const { data, error } = useQuery<string | null>({
    gcTime: cacheTimes.extended,
    queryFn: async () => {
      const { data: authData } = await supabase.auth.getUser();
      return authData.user?.id ?? null;
    },
    queryKey: [...queryKeys.auth.user(), "id"],
    staleTime: Infinity,
    throwOnError: false,
  });

  return error ? null : (data ?? null);
}
