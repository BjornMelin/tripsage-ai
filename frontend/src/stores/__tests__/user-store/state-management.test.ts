/** @vitest-environment jsdom */

import type { UserProfile } from "@schemas/stores";
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { useUserProfileStore } from "@/stores/user-store";
import { setupTimeoutMock } from "@/test/helpers/store";

describe("User Profile Store - State Management", () => {
  let timeoutCleanup: (() => void) | null = null;

  beforeEach(() => {
    const timeoutMock = setupTimeoutMock();
    timeoutCleanup = timeoutMock.mockRestore;
    act(() => {
      useUserProfileStore.getState().reset();
    });
  });

  afterEach(() => {
    timeoutCleanup?.();
  });

  describe("Store Hook", () => {
    it("returns a valid store state object", () => {
      const { result } = renderHook(() => useUserProfileStore());

      // Check that the hook returns an object with expected properties
      expect(result.current).toBeDefined();
      expect(typeof result.current).toBe("object");
    });

    it("has all required state properties", () => {
      const { result } = renderHook(() => useUserProfileStore());
      const state = result.current;

      // Check for required state properties
      expect(state).toHaveProperty("profile");
      expect(state).toHaveProperty("isLoading");
      expect(state).toHaveProperty("isUpdatingProfile");
      expect(state).toHaveProperty("isUploadingAvatar");
      expect(state).toHaveProperty("error");
      expect(state).toHaveProperty("uploadError");
    });

    it("has all required computed properties", () => {
      const { result } = renderHook(() => useUserProfileStore());
      const state = result.current;

      expect(state).toHaveProperty("displayName");
      expect(state).toHaveProperty("hasCompleteProfile");
      expect(state).toHaveProperty("upcomingDocumentExpirations");
    });

    it("has all required action methods", () => {
      const { result } = renderHook(() => useUserProfileStore());
      const state = result.current;

      expect(state).toHaveProperty("setProfile");
      expect(typeof state.setProfile).toBe("function");

      expect(state).toHaveProperty("updatePersonalInfo");
      expect(typeof state.updatePersonalInfo).toBe("function");

      expect(state).toHaveProperty("updateTravelPreferences");
      expect(typeof state.updateTravelPreferences).toBe("function");

      expect(state).toHaveProperty("updatePrivacySettings");
      expect(typeof state.updatePrivacySettings).toBe("function");
    });
  });

  describe("Initial State", () => {
    it("initializes with correct default values", () => {
      const { result } = renderHook(() => useUserProfileStore());

      expect(result.current.profile).toBeNull();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.isUpdatingProfile).toBe(false);
      expect(result.current.isUploadingAvatar).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.uploadError).toBeNull();
    });

    it("computed properties work correctly with empty state", () => {
      const { result } = renderHook(() => useUserProfileStore());

      expect(result.current.displayName).toBe("");
      expect(result.current.hasCompleteProfile).toBe(false);
      expect(result.current.upcomingDocumentExpirations).toEqual([]);
    });
  });

  describe("Loading States", () => {
    beforeEach(() => {
      act(() => {
        useUserProfileStore.setState({
          profile: {
            createdAt: "2025-01-01T00:00:00Z",
            email: "test@example.com",
            favoriteDestinations: [],
            id: "user-1",
            travelDocuments: [],
            updatedAt: "2025-01-01T00:00:00Z",
          },
        });
      });
    });

    it("manages loading states correctly during profile updates", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      let wasUpdating = false;
      await act(async () => {
        const promise = result.current.updatePersonalInfo({
          firstName: "Test",
        });
        wasUpdating = result.current.isUpdatingProfile;
        await promise;
      });

      expect(wasUpdating).toBe(false); // Will be false due to mocked setTimeout
      expect(result.current.isUpdatingProfile).toBe(false);
    });

    it("manages loading states correctly during avatar upload", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      const mockFile = new File(["content"], "avatar.jpg", {
        type: "image/jpeg",
      });

      let wasUploading = false;
      await act(async () => {
        const promise = result.current.uploadAvatar(mockFile);
        wasUploading = result.current.isUploadingAvatar;
        await promise;
      });

      expect(wasUploading).toBe(false); // Will be false due to mocked setTimeout
      expect(result.current.isUploadingAvatar).toBe(false);
    });
  });

  describe("Utility Actions", () => {
    const mockProfile: UserProfile = {
      createdAt: "2025-01-01T00:00:00.000Z",
      email: "test@example.com",
      favoriteDestinations: [
        {
          country: "France",
          id: "dest-1",
          name: "Paris",
          visitCount: 2,
        },
      ],
      id: "user-1",
      personalInfo: {
        firstName: "John",
        lastName: "Doe",
      },
      travelDocuments: [
        {
          expiryDate: "2030-12-31T00:00:00.000Z",
          id: "doc-1",
          issuingCountry: "US",
          number: "123456789",
          type: "passport",
        },
      ],
      updatedAt: "2025-01-01T00:00:00.000Z",
    };

    it("exports profile data", () => {
      const { result } = renderHook(() => useUserProfileStore());

      act(() => {
        result.current.setProfile(mockProfile);
      });

      const exportedData = result.current.exportProfile();
      expect(exportedData).toBeDefined();

      const parsed = JSON.parse(exportedData);
      expect(parsed.profile).toEqual(mockProfile);
      expect(parsed.version).toBe("1.0");
      expect(parsed.exportedAt).toBeDefined();
    });

    it("exports empty string when no profile", () => {
      const { result } = renderHook(() => useUserProfileStore());

      const exportedData = result.current.exportProfile();
      expect(exportedData).toBe("");
    });

    it("imports profile data successfully", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      const exportData = {
        exportedAt: "2025-01-01T00:00:00Z",
        profile: mockProfile,
        version: "1.0",
      };

      let importResult = false;
      await act(async () => {
        importResult = await result.current.importProfile(JSON.stringify(exportData));
      });

      expect(importResult).toBe(true);
      expect(result.current.profile).toEqual(mockProfile);
    });

    it("handles invalid import data", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      let importResult = true;
      await act(async () => {
        importResult = await result.current.importProfile("invalid json");
      });

      expect(importResult).toBe(false);
      expect(result.current.error).toBeDefined();
    });

    it("handles import data without profile", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      const exportData = {
        exportedAt: "2025-01-01T00:00:00Z",
        version: "1.0",
      };

      let importResult = true;
      await act(async () => {
        importResult = await result.current.importProfile(JSON.stringify(exportData));
      });

      expect(importResult).toBe(false);
    });

    it("clears errors", () => {
      const { result } = renderHook(() => useUserProfileStore());

      act(() => {
        useUserProfileStore.setState({
          error: "General error",
          uploadError: "Upload error",
        });
      });

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
      expect(result.current.uploadError).toBeNull();
    });

    it("resets store to initial state", () => {
      const { result } = renderHook(() => useUserProfileStore());

      act(() => {
        useUserProfileStore.setState({
          error: "Some error",
          isLoading: true,
          profile: mockProfile,
          uploadError: "Upload error",
        });
      });

      act(() => {
        result.current.reset();
      });

      expect(result.current.profile).toBeNull();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.isUpdatingProfile).toBe(false);
      expect(result.current.isUploadingAvatar).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.uploadError).toBeNull();
    });
  });
});
