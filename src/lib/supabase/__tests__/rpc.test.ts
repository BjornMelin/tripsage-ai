/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TypedAdminSupabase } from "../admin";

describe("rpc helpers", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("calls insert_user_api_key with normalized service", async () => {
    const rpc = vi.fn().mockResolvedValue({ data: null, error: null });
    const mockClient = { rpc } as unknown as TypedAdminSupabase;
    const { insertUserApiKey } = await import("../rpc");
    await insertUserApiKey("user-1", "OpenAI", "sk-test", mockClient);
    expect(rpc).toHaveBeenCalledWith("insert_user_api_key", {
      p_api_key: "sk-test",
      p_service: "openai",
      p_user_id: "user-1",
    });
  });

  it("calls delete_user_api_key with normalized service", async () => {
    const rpc = vi.fn().mockResolvedValue({ data: null, error: null });
    const mockClient = { rpc } as unknown as TypedAdminSupabase;
    const { deleteUserApiKey } = await import("../rpc");
    await deleteUserApiKey("user-1", "xai", mockClient);
    expect(rpc).toHaveBeenCalledWith("delete_user_api_key", {
      p_service: "xai",
      p_user_id: "user-1",
    });
  });

  it("returns value from get_user_api_key", async () => {
    const rpc = vi.fn().mockResolvedValue({ data: "secret", error: null });
    const mockClient = { rpc } as unknown as TypedAdminSupabase;
    const { getUserApiKey } = await import("../rpc");
    const res = await getUserApiKey("user-1", "openrouter", mockClient);
    expect(res).toBe("secret");
  });

  it("throws on invalid service", async () => {
    const { insertUserApiKey } = await import("../rpc");
    await expect(insertUserApiKey("u", "bad", "k")).rejects.toThrow("Invalid service");
  });
});
