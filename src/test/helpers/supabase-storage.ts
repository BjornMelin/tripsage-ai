import type { SupabaseClient } from "@supabase/supabase-js";
import { vi } from "vitest";
import type { Database } from "@/lib/supabase/database.types";

type StorageBucketApi = ReturnType<SupabaseClient<Database>["storage"]["from"]>;

export type StorageFromHandlers = Partial<{
  createSignedUrl: StorageBucketApi["createSignedUrl"];
  createSignedUrls: StorageBucketApi["createSignedUrls"];
  remove: StorageBucketApi["remove"];
  upload: StorageBucketApi["upload"];
}>;

export function setupStorageFromMock(
  supabase: SupabaseClient<Database>,
  handlers: StorageFromHandlers
): void {
  const originalFrom = supabase.storage.from.bind(supabase.storage);
  vi.spyOn(supabase.storage, "from").mockImplementation((bucket) => {
    const api = originalFrom(bucket);
    if (handlers.createSignedUrl) {
      vi.spyOn(api, "createSignedUrl").mockImplementation(handlers.createSignedUrl);
    }
    if (handlers.createSignedUrls) {
      vi.spyOn(api, "createSignedUrls").mockImplementation(handlers.createSignedUrls);
    }
    if (handlers.remove) {
      vi.spyOn(api, "remove").mockImplementation(handlers.remove);
    }
    if (handlers.upload) {
      vi.spyOn(api, "upload").mockImplementation(handlers.upload);
    }
    return api;
  });
}
