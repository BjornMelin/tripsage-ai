/**
 * @fileoverview React Query hook for retrieving the current Supabase user id.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { keys } from "@/lib/keys";
import { cacheTimes } from "@/lib/query/config";
import { useSupabaseRequired } from "@/lib/supabase";

export function useCurrentUserId(): string | null {
  const supabase = useSupabaseRequired();

  const { data, error } = useQuery<string | null>({
    gcTime: cacheTimes.extended,
    queryFn: async () => {
      const { data: authData } = await supabase.auth.getUser();
      return authData.user?.id ?? null;
    },
    queryKey: keys.auth.userId(),
    staleTime: Infinity,
    throwOnError: false,
  });

  return error ? null : (data ?? null);
}
