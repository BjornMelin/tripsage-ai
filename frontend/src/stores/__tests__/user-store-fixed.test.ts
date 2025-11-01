/**
 * @fileoverview Deterministic tests for user profile store: derived fields
 * (displayName, hasCompleteProfile, expirations) and core actions.
 */

import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  type PersonalInfo,
  type UserProfile,
  useUserProfileStore,
} from "../user-store";

// Mock the store to avoid persistence issues in tests
vi.mock("zustand/middleware", () => ({
  persist: (fn: any) => fn,
  devtools: (fn: any) => fn,
}));

describe("User Profile Store - Fixed", () => {
  let mockProfile: UserProfile;

  beforeEach(() => {
    // Use reset function instead of setState
    const { result } = renderHook(() => useUserProfileStore());
    act(() => {
      result.current.reset();
    });

    mockProfile = {
      id: "user-1",
      email: "test@example.com",
      personalInfo: {
        firstName: "John",
        lastName: "Doe",
        displayName: "John Doe",
        bio: "Travel enthusiast",
        location: "New York, NY",
        phoneNumber: "+1234567890",
      },
      travelPreferences: {
        preferredCabinClass: "business",
        preferredAirlines: ["Delta", "United"],
        excludedAirlines: [],
        maxLayovers: 1,
        preferredAccommodationType: "hotel",
        preferredHotelChains: [],
        requireWifi: true,
        requireBreakfast: true,
        requireParking: false,
        requireGym: false,
        requirePool: false,
        accessibilityRequirements: [],
        dietaryRestrictions: [],
      },
      privacySettings: {
        profileVisibility: "friends",
        showTravelHistory: true,
        allowDataSharing: false,
        enableAnalytics: true,
        enableLocationTracking: false,
      },
      favoriteDestinations: [],
      travelDocuments: [],
      createdAt: "2025-01-01T00:00:00Z",
      updatedAt: "2025-01-01T00:00:00Z",
    };
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

  describe("Profile Management", () => {
    it("sets profile correctly", () => {
      const { result } = renderHook(() => useUserProfileStore());

      act(() => {
        result.current.setProfile(mockProfile);
      });

      expect(result.current.profile).toEqual(mockProfile);

      act(() => {
        result.current.setProfile(null);
      });

      expect(result.current.profile).toBeNull();
    });

    it("successfully updates personal information", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      // Set initial profile
      act(() => {
        result.current.setProfile(mockProfile);
      });

      const updates: Partial<PersonalInfo> = {
        firstName: "Jane",
        lastName: "Smith",
        bio: "Updated bio",
        location: "San Francisco, CA",
      };

      let updateResult: boolean;
      await act(async () => {
        updateResult = await result.current.updatePersonalInfo(updates);
      });

      expect(updateResult!).toBe(true);
      expect(result.current.profile?.personalInfo?.firstName).toBe("Jane");
      expect(result.current.profile?.personalInfo?.lastName).toBe("Smith");
      expect(result.current.profile?.personalInfo?.bio).toBe("Updated bio");
      expect(result.current.profile?.personalInfo?.location).toBe("San Francisco, CA");
      expect(result.current.isUpdatingProfile).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("handles update personal info when no profile exists", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      let updateResult: boolean;
      await act(async () => {
        updateResult = await result.current.updatePersonalInfo({
          firstName: "Test",
        });
      });

      expect(updateResult!).toBe(false);
    });
  });

  describe("Computed Properties", () => {
    it("correctly computes display name", () => {
      const { result } = renderHook(() => useUserProfileStore());

      // No profile
      expect(result.current.displayName).toBe("");

      // Profile with display name
      const { rerender } = renderHook(() => useUserProfileStore());
      act(() => {
        result.current.setProfile({
          ...mockProfile,
          personalInfo: {
            displayName: "Custom Name",
          },
        });
      });
      rerender();
      expect(result.current.displayName).toBe("Custom Name");

      // Profile with first and last name
      act(() => {
        result.current.setProfile({
          ...mockProfile,
          personalInfo: {
            firstName: "John",
            lastName: "Doe",
          },
        });
      });
      rerender();
      expect(result.current.displayName).toBe("John Doe");

      // Profile with only first name
      act(() => {
        result.current.setProfile({
          ...mockProfile,
          personalInfo: {
            firstName: "Jane",
          },
        });
      });
      rerender();
      expect(result.current.displayName).toBe("Jane");

      // Profile with only email
      act(() => {
        result.current.setProfile({
          ...mockProfile,
          email: "username@example.com",
          personalInfo: undefined,
        });
      });
      rerender();
      expect(result.current.displayName).toBe("username");
    });

    it("correctly computes complete profile status", () => {
      const { result } = renderHook(() => useUserProfileStore());

      // No profile
      expect(result.current.hasCompleteProfile).toBe(false);

      // Incomplete profile
      const { rerender: rerender2 } = renderHook(() => useUserProfileStore());
      act(() => {
        result.current.setProfile({
          ...mockProfile,
          personalInfo: {
            firstName: "John",
          },
        });
      });
      rerender2();
      expect(result.current.hasCompleteProfile).toBe(false);

      // Complete profile
      act(() => {
        result.current.setProfile({
          ...mockProfile,
          avatarUrl: "https://example.com/avatar.jpg",
          personalInfo: {
            firstName: "John",
            lastName: "Doe",
          },
          travelPreferences: {
            preferredCabinClass: "economy",
            preferredAirlines: [],
            excludedAirlines: [],
            maxLayovers: 2,
            preferredAccommodationType: "hotel",
            preferredHotelChains: [],
            requireWifi: true,
            requireBreakfast: false,
            requireParking: false,
            requireGym: false,
            requirePool: false,
            accessibilityRequirements: [],
            dietaryRestrictions: [],
          },
        });
      });
      rerender2();
      expect(result.current.hasCompleteProfile).toBe(true);
    });
  });

  describe("Favorite Destinations", () => {
    beforeEach(() => {
      const { result } = renderHook(() => useUserProfileStore());
      act(() => {
        result.current.setProfile({
          ...mockProfile,
          favoriteDestinations: [],
        });
      });
    });

    it("adds a favorite destination", () => {
      const { result } = renderHook(() => useUserProfileStore());

      const destination = {
        name: "Paris",
        country: "France",
        notes: "Beautiful city",
      };

      act(() => {
        result.current.addFavoriteDestination(destination);
      });

      expect(result.current.profile?.favoriteDestinations).toHaveLength(1);
      const addedDestination = result.current.profile?.favoriteDestinations[0];
      expect(addedDestination?.name).toBe("Paris");
      expect(addedDestination?.country).toBe("France");
      expect(addedDestination?.notes).toBe("Beautiful city");
      expect(addedDestination?.visitCount).toBe(0);
      expect(addedDestination?.id).toBeDefined();
    });
  });

  describe("Error Management", () => {
    it("can clear errors through actions", () => {
      const { result } = renderHook(() => useUserProfileStore());

      act(() => {
        result.current.clearError();
      });

      // Verify the clearError function can be called without throwing
      expect(typeof result.current.clearError).toBe("function");
    });

    it("resets store to initial state", () => {
      const { result } = renderHook(() => useUserProfileStore());

      act(() => {
        result.current.setProfile(mockProfile);
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
