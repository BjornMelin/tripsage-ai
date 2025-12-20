/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockSupabaseClient, getSupabaseMockState } from "@/test/mocks/supabase";

describe("rpc helpers", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("calls insert_user_api_key with normalized service", async () => {
    const mockClient = createMockSupabaseClient();
    const rpcSpy = vi.spyOn(mockClient, "rpc");
    const { insertUserApiKey } = await import("../rpc");
    await insertUserApiKey("user-1", "OpenAI", "sk-test", mockClient);
    expect(rpcSpy).toHaveBeenCalledWith("insert_user_api_key", {
      p_api_key: "sk-test",
      p_service: "openai",
      p_user_id: "user-1",
    });
  });

  it("calls delete_user_api_key with normalized service", async () => {
    const mockClient = createMockSupabaseClient();
    const rpcSpy = vi.spyOn(mockClient, "rpc");
    const { deleteUserApiKey } = await import("../rpc");
    await deleteUserApiKey("user-1", "xai", mockClient);
    expect(rpcSpy).toHaveBeenCalledWith("delete_user_api_key", {
      p_service: "xai",
      p_user_id: "user-1",
    });
  });

  it("returns value from get_user_api_key", async () => {
    const mockClient = createMockSupabaseClient();
    getSupabaseMockState(mockClient).rpcResults.set("get_user_api_key", {
      data: "secret",
      error: null,
    });
    const { getUserApiKey } = await import("../rpc");
    const res = await getUserApiKey("user-1", "openrouter", mockClient);
    expect(res).toBe("secret");
  });

  it("throws on invalid service", async () => {
    const { insertUserApiKey } = await import("../rpc");
    await expect(insertUserApiKey("u", "bad", "k")).rejects.toThrow("Invalid service");
  });
});
