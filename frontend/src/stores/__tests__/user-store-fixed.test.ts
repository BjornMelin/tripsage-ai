/**
 * @vitest-environment node
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setupSupabaseMocks } from "@/test/mocks/supabase";
import type { PersonalInfo, UserProfile } from "../user-store";
import { useUserProfileStore } from "../user-store";

setupSupabaseMocks();

// Mock the store to avoid persistence issues in tests
vi.mock("zustand/middleware", () => ({
  // biome-ignore lint/suspicious/noExplicitAny: Test mock doesn't need type safety
  devtools: (fn: any) => fn,
  // biome-ignore lint/suspicious/noExplicitAny: Test mock doesn't need type safety
  persist: (fn: any) => fn,
}));

describe("User Profile Store - Fixed", () => {
  let mockProfile: UserProfile;

  beforeEach(() => {
    vi.useFakeTimers();
    useUserProfileStore.getState().reset();

    mockProfile = {
      createdAt: "2025-01-01T00:00:00Z",
      email: "test@example.com",
      favoriteDestinations: [],
      id: "user-1",
      personalInfo: {
        bio: "Travel enthusiast",
        displayName: "John Doe",
        firstName: "John",
        lastName: "Doe",
        location: "New York, NY",
        phoneNumber: "+1234567890",
      },
      privacySettings: {
        allowDataSharing: false,
        enableAnalytics: true,
        enableLocationTracking: false,
        profileVisibility: "friends",
        showTravelHistory: true,
      },
      travelDocuments: [],
      travelPreferences: {
        accessibilityRequirements: [],
        dietaryRestrictions: [],
        excludedAirlines: [],
        maxLayovers: 2,
        preferredAccommodationType: "hotel",
        preferredAirlines: [],
        preferredCabinClass: "economy",
        preferredHotelChains: [],
        requireBreakfast: false,
        requireGym: false,
        requireParking: false,
        requirePool: false,
        requireWifi: true,
      },
      updatedAt: "2025-01-01T00:00:00Z",
    };
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("Profile Management", () => {
    it("successfully updates personal information", async () => {
      const store = useUserProfileStore.getState();
      store.setProfile(mockProfile);

      const updates: Partial<PersonalInfo> = {
        bio: "Updated bio",
        firstName: "Jane",
        lastName: "Smith",
        location: "San Francisco, CA",
      };

      const updatePromise = store.updatePersonalInfo(updates);
      await vi.runAllTimersAsync();
      const updateResult = await updatePromise;

      expect(updateResult).toBe(true);
      expect(store.profile?.personalInfo?.firstName).toBe("Jane");
      expect(store.profile?.personalInfo?.lastName).toBe("Smith");
      expect(store.profile?.personalInfo?.bio).toBe("Updated bio");
      expect(store.profile?.personalInfo?.location).toBe("San Francisco, CA");
      expect(store.isUpdatingProfile).toBe(false);
      expect(store.error).toBeNull();
    });

    it("handles update personal info when no profile exists", async () => {
      const store = useUserProfileStore.getState();
      const updatePromise = store.updatePersonalInfo({
        firstName: "Test",
      });
      await vi.runAllTimersAsync();
      const updateResult = await updatePromise;

      expect(updateResult).toBe(false);
    });

    it("loads profile successfully", () => {
      const store = useUserProfileStore.getState();
      store.setProfile(mockProfile);

      expect(store.profile).toMatchObject(mockProfile);
      expect(store.displayName).toBe("John Doe");
    });

    it("resets profile to null", () => {
      const store = useUserProfileStore.getState();
      store.setProfile(mockProfile);
      expect(store.profile).not.toBeNull();

      store.reset();
      expect(store.profile).toBeNull();
    });
  });
});
