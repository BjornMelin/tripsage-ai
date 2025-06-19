import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { type UserProfile, useUserProfileStore } from "../user-store";

// Mock the store to avoid persistence issues in tests
vi.mock("zustand/middleware", () => ({
  persist: (fn: any) => fn,
  devtools: (fn: any) => fn,
}));

describe("User Profile Store - Simple Test", () => {
  beforeEach(() => {
    act(() => {
      useUserProfileStore.setState({
        profile: null,
        isLoading: false,
        isUpdatingProfile: false,
        isUploadingAvatar: false,
        error: null,
        uploadError: null,
      });
    });
  });

  it("should initialize with correct default values", () => {
    const { result } = renderHook(() => useUserProfileStore());

    expect(result.current.profile).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isUpdatingProfile).toBe(false);
    expect(result.current.isUploadingAvatar).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.uploadError).toBeNull();
  });

  it("should have computed properties", () => {
    const { result } = renderHook(() => useUserProfileStore());

    expect(result.current.displayName).toBe("");
    expect(result.current.hasCompleteProfile).toBe(false);
    expect(result.current.upcomingDocumentExpirations).toEqual([]);
  });

  it("should set profile", () => {
    const { result } = renderHook(() => useUserProfileStore());

    const mockProfile: UserProfile = {
      id: "user-1",
      email: "test@example.com",
      favoriteDestinations: [],
      travelDocuments: [],
      createdAt: "2025-01-01T00:00:00Z",
      updatedAt: "2025-01-01T00:00:00Z",
    };

    act(() => {
      result.current.setProfile(mockProfile);
    });

    expect(result.current.profile).toEqual(mockProfile);
  });
});
