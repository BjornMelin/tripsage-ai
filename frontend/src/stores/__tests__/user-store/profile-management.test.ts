/** @vitest-environment jsdom */

import type {
  PersonalInfo,
  PrivacySettings,
  TravelPreferences,
  UserProfile,
} from "@schemas/stores";
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { useUserProfileStore } from "@/stores/user-store";
import { setupTimeoutMock } from "@/test/store-helpers";

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

describe("User Profile Store - Profile Management", () => {
  const mockProfile: UserProfile = {
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
      maxLayovers: 1,
      preferredAccommodationType: "hotel",
      preferredAirlines: ["Delta", "United"],
      preferredCabinClass: "business",
      preferredHotelChains: [],
      requireBreakfast: true,
      requireGym: false,
      requireParking: false,
      requirePool: false,
      requireWifi: true,
    },
    updatedAt: "2025-01-01T00:00:00Z",
  };

  beforeEach(() => {
    act(() => {
      useUserProfileStore.getState().reset();
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

    describe("Update Personal Info", () => {
      beforeEach(() => {
        act(() => {
          useUserProfileStore.setState({ profile: mockProfile });
        });
      });

      it("successfully updates personal information", async () => {
        const { result } = renderHook(() => useUserProfileStore());

        const updates: Partial<PersonalInfo> = {
          bio: "Updated bio",
          firstName: "Jane",
          lastName: "Smith",
          location: "San Francisco, CA",
        };

        let updateResult = false;
        await act(async () => {
          updateResult = await result.current.updatePersonalInfo(updates);
        });

        expect(updateResult).toBe(true);
        expect(result.current.profile?.personalInfo?.firstName).toBe("Jane");
        expect(result.current.profile?.personalInfo?.lastName).toBe("Smith");
        expect(result.current.profile?.personalInfo?.bio).toBe("Updated bio");
        expect(result.current.profile?.personalInfo?.location).toBe(
          "San Francisco, CA"
        );
        expect(result.current.isUpdatingProfile).toBe(false);
        expect(result.current.error).toBeNull();
      });

      it("handles update personal info when no profile exists", async () => {
        const { result } = renderHook(() => useUserProfileStore());

        // Clear profile
        act(() => {
          result.current.setProfile(null);
        });

        let updateResult = true;
        await act(async () => {
          updateResult = await result.current.updatePersonalInfo({
            firstName: "Test",
          });
        });

        expect(updateResult).toBe(false);
      });

      it("preserves existing personal info when updating partial data", async () => {
        const { result } = renderHook(() => useUserProfileStore());

        const updates: Partial<PersonalInfo> = {
          bio: "Just updated bio",
        };

        await act(async () => {
          await result.current.updatePersonalInfo(updates);
        });

        expect(result.current.profile?.personalInfo?.firstName).toBe("John");
        expect(result.current.profile?.personalInfo?.lastName).toBe("Doe");
        expect(result.current.profile?.personalInfo?.bio).toBe("Just updated bio");
      });
    });

    describe("Update Travel Preferences", () => {
      beforeEach(() => {
        act(() => {
          useUserProfileStore.setState({ profile: mockProfile });
        });
      });

      it("successfully updates travel preferences", async () => {
        const { result } = renderHook(() => useUserProfileStore());

        const updates: Partial<TravelPreferences> = {
          maxLayovers: 0,
          preferredAirlines: ["Lufthansa", "Emirates"],
          preferredCabinClass: "first",
          requireBreakfast: false,
          requirePool: true,
        };

        let updateResult = false;
        await act(async () => {
          updateResult = await result.current.updateTravelPreferences(updates);
        });

        expect(updateResult).toBe(true);
        expect(result.current.profile?.travelPreferences?.preferredCabinClass).toBe(
          "first"
        );
        expect(result.current.profile?.travelPreferences?.maxLayovers).toBe(0);
        expect(result.current.profile?.travelPreferences?.preferredAirlines).toEqual([
          "Lufthansa",
          "Emirates",
        ]);
        expect(result.current.profile?.travelPreferences?.requireBreakfast).toBe(false);
        expect(result.current.profile?.travelPreferences?.requirePool).toBe(true);
      });

      it("handles update when no profile exists", async () => {
        const { result } = renderHook(() => useUserProfileStore());

        act(() => {
          result.current.setProfile(null);
        });

        let updateResult = true;
        await act(async () => {
          updateResult = await result.current.updateTravelPreferences({
            preferredCabinClass: "economy",
          });
        });

        expect(updateResult).toBe(false);
      });

      it("preserves existing preferences when updating partial data", async () => {
        const { result } = renderHook(() => useUserProfileStore());

        await act(async () => {
          await result.current.updateTravelPreferences({
            maxLayovers: 2,
          });
        });

        expect(result.current.profile?.travelPreferences?.preferredCabinClass).toBe(
          "business"
        );
        expect(result.current.profile?.travelPreferences?.maxLayovers).toBe(2);
        expect(result.current.profile?.travelPreferences?.requireWifi).toBe(true);
      });
    });

    describe("Update Privacy Settings", () => {
      beforeEach(() => {
        act(() => {
          useUserProfileStore.setState({ profile: mockProfile });
        });
      });

      it("successfully updates privacy settings", async () => {
        const { result } = renderHook(() => useUserProfileStore());

        const updates: Partial<PrivacySettings> = {
          allowDataSharing: true,
          enableAnalytics: false,
          profileVisibility: "public",
          showTravelHistory: false,
        };

        let updateResult = false;
        await act(async () => {
          updateResult = await result.current.updatePrivacySettings(updates);
        });

        expect(updateResult).toBe(true);
        expect(result.current.profile?.privacySettings?.profileVisibility).toBe(
          "public"
        );
        expect(result.current.profile?.privacySettings?.showTravelHistory).toBe(false);
        expect(result.current.profile?.privacySettings?.allowDataSharing).toBe(true);
        expect(result.current.profile?.privacySettings?.enableAnalytics).toBe(false);
      });

      it("handles update when no profile exists", async () => {
        const { result } = renderHook(() => useUserProfileStore());

        act(() => {
          result.current.setProfile(null);
        });

        let updateResult = true;
        await act(async () => {
          updateResult = await result.current.updatePrivacySettings({
            profileVisibility: "private",
          });
        });

        expect(updateResult).toBe(false);
      });
    });
  });
});
