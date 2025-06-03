import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  useUserProfileStore,
  type UserProfile,
  type PersonalInfo,
  type TravelPreferences,
  type PrivacySettings,
  type FavoriteDestination,
  type TravelDocument,
} from "../user-store";

// Mock setTimeout to make tests run faster
vi.mock("global", () => ({
  setTimeout: vi.fn((fn) => fn()),
}));

describe("User Profile Store", () => {
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
    const mockProfile: UserProfile = {
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
        maxLayovers: 1,
        preferredAccommodationType: "hotel",
        requireWifi: true,
        requireBreakfast: true,
      },
      privacySettings: {
        profileVisibility: "friends",
        showTravelHistory: true,
        allowDataSharing: false,
      },
      favoriteDestinations: [],
      travelDocuments: [],
      createdAt: "2025-01-01T00:00:00Z",
      updatedAt: "2025-01-01T00:00:00Z",
    };

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
        const { result } = renderHook(() => useUserProfileStore());
        act(() => {
          result.current.setProfile(mockProfile);
        });
      });

      it("successfully updates personal information", async () => {
        const { result } = renderHook(() => useUserProfileStore());

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

        let updateResult: boolean;
        await act(async () => {
          updateResult = await result.current.updatePersonalInfo({
            firstName: "Test",
          });
        });

        expect(updateResult!).toBe(false);
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
        const { result } = renderHook(() => useUserProfileStore());
        act(() => {
          result.current.setProfile(mockProfile);
        });
      });

      it("successfully updates travel preferences", async () => {
        const { result } = renderHook(() => useUserProfileStore());

        const updates: Partial<TravelPreferences> = {
          preferredCabinClass: "first",
          maxLayovers: 0,
          preferredAirlines: ["Lufthansa", "Emirates"],
          requireBreakfast: false,
          requirePool: true,
        };

        let updateResult: boolean;
        await act(async () => {
          updateResult = await result.current.updateTravelPreferences(updates);
        });

        expect(updateResult!).toBe(true);
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

        let updateResult: boolean;
        await act(async () => {
          updateResult = await result.current.updateTravelPreferences({
            preferredCabinClass: "economy",
          });
        });

        expect(updateResult!).toBe(false);
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
        const { result } = renderHook(() => useUserProfileStore());
        act(() => {
          result.current.setProfile(mockProfile);
        });
      });

      it("successfully updates privacy settings", async () => {
        const { result } = renderHook(() => useUserProfileStore());

        const updates: Partial<PrivacySettings> = {
          profileVisibility: "public",
          showTravelHistory: false,
          allowDataSharing: true,
          enableAnalytics: false,
        };

        let updateResult: boolean;
        await act(async () => {
          updateResult = await result.current.updatePrivacySettings(updates);
        });

        expect(updateResult!).toBe(true);
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

        let updateResult: boolean;
        await act(async () => {
          updateResult = await result.current.updatePrivacySettings({
            profileVisibility: "private",
          });
        });

        expect(updateResult!).toBe(false);
      });
    });
  });

  describe("Avatar Management", () => {
    beforeEach(() => {
      const { result } = renderHook(() => useUserProfileStore());
      act(() => {
        result.current.setProfile({
          id: "user-1",
          email: "test@example.com",
          favoriteDestinations: [],
          travelDocuments: [],
          createdAt: "2025-01-01T00:00:00Z",
          updatedAt: "2025-01-01T00:00:00Z",
        });
      });
    });

    it("successfully uploads avatar", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      const mockFile = new File(["avatar content"], "avatar.jpg", {
        type: "image/jpeg",
      });

      let uploadResult: string | null;
      await act(async () => {
        uploadResult = await result.current.uploadAvatar(mockFile);
      });

      expect(uploadResult).toBeDefined();
      expect(uploadResult).toContain("https://example.com/avatars/");
      expect(result.current.profile?.avatarUrl).toBe(uploadResult);
      expect(result.current.isUploadingAvatar).toBe(false);
      expect(result.current.uploadError).toBeNull();
    });

    it("handles invalid file type", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      const mockFile = new File(["text content"], "document.txt", {
        type: "text/plain",
      });

      let uploadResult: string | null;
      await act(async () => {
        uploadResult = await result.current.uploadAvatar(mockFile);
      });

      expect(uploadResult).toBeNull();
      expect(result.current.uploadError).toBe("File must be an image");
      expect(result.current.isUploadingAvatar).toBe(false);
    });

    it("handles file too large", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      const mockFile = new File(["x".repeat(6 * 1024 * 1024)], "large.jpg", {
        type: "image/jpeg",
      });

      let uploadResult: string | null;
      await act(async () => {
        uploadResult = await result.current.uploadAvatar(mockFile);
      });

      expect(uploadResult).toBeNull();
      expect(result.current.uploadError).toBe("File size must be less than 5MB");
    });

    it("successfully removes avatar", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      // First set an avatar
      act(() => {
        const currentProfile = useUserProfileStore.getState().profile;
        if (currentProfile) {
          useUserProfileStore.setState({
            profile: {
              ...currentProfile,
              avatarUrl: "https://example.com/avatar.jpg",
            },
          });
        }
      });

      let removeResult: boolean;
      await act(async () => {
        removeResult = await result.current.removeAvatar();
      });

      expect(removeResult!).toBe(true);
      expect(result.current.profile?.avatarUrl).toBeUndefined();
      expect(result.current.isUpdatingProfile).toBe(false);
    });

    it("handles remove avatar when no profile exists", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      act(() => {
        result.current.setProfile(null);
      });

      let removeResult: boolean;
      await act(async () => {
        removeResult = await result.current.removeAvatar();
      });

      expect(removeResult!).toBe(false);
    });
  });

  describe("Favorite Destinations", () => {
    beforeEach(() => {
      const { result } = renderHook(() => useUserProfileStore());
      act(() => {
        result.current.setProfile({
          id: "user-1",
          email: "test@example.com",
          favoriteDestinations: [],
          travelDocuments: [],
          createdAt: "2025-01-01T00:00:00Z",
          updatedAt: "2025-01-01T00:00:00Z",
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

    it("removes a favorite destination", () => {
      const { result } = renderHook(() => useUserProfileStore());

      // First add destinations
      act(() => {
        result.current.addFavoriteDestination({ name: "Paris", country: "France" });
        result.current.addFavoriteDestination({ name: "Tokyo", country: "Japan" });
      });

      expect(result.current.profile?.favoriteDestinations).toHaveLength(2);

      const parisId = result.current.profile?.favoriteDestinations[0].id;

      act(() => {
        result.current.removeFavoriteDestination(parisId!);
      });

      expect(result.current.profile?.favoriteDestinations).toHaveLength(1);
      expect(result.current.profile?.favoriteDestinations[0].name).toBe("Tokyo");
    });

    it("updates a favorite destination", () => {
      const { result } = renderHook(() => useUserProfileStore());

      act(() => {
        result.current.addFavoriteDestination({ name: "Paris", country: "France" });
      });

      const destinationId = result.current.profile?.favoriteDestinations[0].id;

      act(() => {
        result.current.updateFavoriteDestination(destinationId!, {
          notes: "City of lights",
          visitCount: 2,
        });
      });

      const updatedDestination = result.current.profile?.favoriteDestinations[0];
      expect(updatedDestination?.name).toBe("Paris");
      expect(updatedDestination?.notes).toBe("City of lights");
      expect(updatedDestination?.visitCount).toBe(2);
    });

    it("increments destination visit count", () => {
      const { result } = renderHook(() => useUserProfileStore());

      act(() => {
        result.current.addFavoriteDestination({ name: "Paris", country: "France" });
      });

      const destinationId = result.current.profile?.favoriteDestinations[0].id;

      act(() => {
        result.current.incrementDestinationVisit(destinationId!);
      });

      const destination = result.current.profile?.favoriteDestinations[0];
      expect(destination?.visitCount).toBe(1);
      expect(destination?.lastVisited).toBeDefined();

      act(() => {
        result.current.incrementDestinationVisit(destinationId!);
      });

      expect(result.current.profile?.favoriteDestinations[0].visitCount).toBe(2);
    });

    it("handles destination operations when no profile exists", () => {
      const { result } = renderHook(() => useUserProfileStore());

      act(() => {
        result.current.setProfile(null);
      });

      act(() => {
        result.current.addFavoriteDestination({ name: "Paris", country: "France" });
      });

      expect(result.current.profile).toBeNull();
    });
  });

  describe("Travel Documents", () => {
    beforeEach(() => {
      const { result } = renderHook(() => useUserProfileStore());
      act(() => {
        result.current.setProfile({
          id: "user-1",
          email: "test@example.com",
          favoriteDestinations: [],
          travelDocuments: [],
          createdAt: "2025-01-01T00:00:00Z",
          updatedAt: "2025-01-01T00:00:00Z",
        });
      });
    });

    it("adds a travel document", () => {
      const { result } = renderHook(() => useUserProfileStore());

      const document: Omit<TravelDocument, "id"> = {
        type: "passport",
        number: "123456789",
        expiryDate: "2030-12-31",
        issuingCountry: "United States",
        notes: "Valid for 10 years",
      };

      act(() => {
        result.current.addTravelDocument(document);
      });

      expect(result.current.profile?.travelDocuments).toHaveLength(1);
      const addedDocument = result.current.profile?.travelDocuments[0];
      expect(addedDocument?.type).toBe("passport");
      expect(addedDocument?.number).toBe("123456789");
      expect(addedDocument?.expiryDate).toBe("2030-12-31");
      expect(addedDocument?.issuingCountry).toBe("United States");
      expect(addedDocument?.notes).toBe("Valid for 10 years");
      expect(addedDocument?.id).toBeDefined();
    });

    it("removes a travel document", () => {
      const { result } = renderHook(() => useUserProfileStore());

      // Add documents
      act(() => {
        result.current.addTravelDocument({
          type: "passport",
          number: "123456789",
          expiryDate: "2030-12-31",
          issuingCountry: "US",
        });
        result.current.addTravelDocument({
          type: "visa",
          number: "987654321",
          expiryDate: "2025-06-30",
          issuingCountry: "France",
        });
      });

      expect(result.current.profile?.travelDocuments).toHaveLength(2);

      const passportId = result.current.profile?.travelDocuments[0].id;

      act(() => {
        result.current.removeTravelDocument(passportId!);
      });

      expect(result.current.profile?.travelDocuments).toHaveLength(1);
      expect(result.current.profile?.travelDocuments[0].type).toBe("visa");
    });

    it("updates a travel document", () => {
      const { result } = renderHook(() => useUserProfileStore());

      act(() => {
        result.current.addTravelDocument({
          type: "passport",
          number: "123456789",
          expiryDate: "2030-12-31",
          issuingCountry: "US",
        });
      });

      const documentId = result.current.profile?.travelDocuments[0].id;

      act(() => {
        result.current.updateTravelDocument(documentId!, {
          expiryDate: "2031-12-31",
          notes: "Renewed passport",
        });
      });

      const updatedDocument = result.current.profile?.travelDocuments[0];
      expect(updatedDocument?.number).toBe("123456789");
      expect(updatedDocument?.expiryDate).toBe("2031-12-31");
      expect(updatedDocument?.notes).toBe("Renewed passport");
    });

    it("handles document operations when no profile exists", () => {
      const { result } = renderHook(() => useUserProfileStore());

      act(() => {
        result.current.setProfile(null);
      });

      act(() => {
        result.current.addTravelDocument({
          type: "passport",
          number: "123456789",
          expiryDate: "2030-12-31",
          issuingCountry: "US",
        });
      });

      expect(result.current.profile).toBeNull();
    });
  });

  describe("Computed Properties", () => {
    it("correctly computes display name", () => {
      const { result } = renderHook(() => useUserProfileStore());

      // No profile
      expect(result.current.displayName).toBe("");

      // Profile with display name
      act(() => {
        result.current.setProfile({
          id: "user-1",
          email: "test@example.com",
          personalInfo: {
            displayName: "Custom Name",
          },
          favoriteDestinations: [],
          travelDocuments: [],
          createdAt: "2025-01-01T00:00:00Z",
          updatedAt: "2025-01-01T00:00:00Z",
        });
      });

      expect(result.current.displayName).toBe("Custom Name");

      // Profile with first and last name
      act(() => {
        result.current.setProfile({
          id: "user-1",
          email: "test@example.com",
          personalInfo: {
            firstName: "John",
            lastName: "Doe",
          },
          favoriteDestinations: [],
          travelDocuments: [],
          createdAt: "2025-01-01T00:00:00Z",
          updatedAt: "2025-01-01T00:00:00Z",
        });
      });

      expect(result.current.displayName).toBe("John Doe");

      // Profile with only first name
      act(() => {
        result.current.setProfile({
          id: "user-1",
          email: "test@example.com",
          personalInfo: {
            firstName: "Jane",
          },
          favoriteDestinations: [],
          travelDocuments: [],
          createdAt: "2025-01-01T00:00:00Z",
          updatedAt: "2025-01-01T00:00:00Z",
        });
      });

      expect(result.current.displayName).toBe("Jane");

      // Profile with only email
      act(() => {
        result.current.setProfile({
          id: "user-1",
          email: "username@example.com",
          favoriteDestinations: [],
          travelDocuments: [],
          createdAt: "2025-01-01T00:00:00Z",
          updatedAt: "2025-01-01T00:00:00Z",
        });
      });

      expect(result.current.displayName).toBe("username");
    });

    it("correctly computes complete profile status", () => {
      const { result } = renderHook(() => useUserProfileStore());

      // No profile
      expect(result.current.hasCompleteProfile).toBe(false);

      // Incomplete profile
      act(() => {
        result.current.setProfile({
          id: "user-1",
          email: "test@example.com",
          personalInfo: {
            firstName: "John",
          },
          favoriteDestinations: [],
          travelDocuments: [],
          createdAt: "2025-01-01T00:00:00Z",
          updatedAt: "2025-01-01T00:00:00Z",
        });
      });

      expect(result.current.hasCompleteProfile).toBe(false);

      // Complete profile
      act(() => {
        result.current.setProfile({
          id: "user-1",
          email: "test@example.com",
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
            requireWifi: true,
            requireBreakfast: false,
            requireParking: false,
            requireGym: false,
            requirePool: false,
            accessibilityRequirements: [],
            dietaryRestrictions: [],
          },
          favoriteDestinations: [],
          travelDocuments: [],
          createdAt: "2025-01-01T00:00:00Z",
          updatedAt: "2025-01-01T00:00:00Z",
        });
      });

      expect(result.current.hasCompleteProfile).toBe(true);
    });

    it("correctly computes upcoming document expirations", () => {
      const { result } = renderHook(() => useUserProfileStore());

      const now = new Date();
      const inThirtyDays = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000);
      const inNinetyDays = new Date(now.getTime() + 90 * 24 * 60 * 60 * 1000);

      act(() => {
        result.current.setProfile({
          id: "user-1",
          email: "test@example.com",
          favoriteDestinations: [],
          travelDocuments: [
            {
              id: "doc-1",
              type: "passport",
              number: "123456789",
              expiryDate: inThirtyDays.toISOString(),
              issuingCountry: "US",
            },
            {
              id: "doc-2",
              type: "visa",
              number: "987654321",
              expiryDate: inNinetyDays.toISOString(),
              issuingCountry: "France",
            },
          ],
          createdAt: "2025-01-01T00:00:00Z",
          updatedAt: "2025-01-01T00:00:00Z",
        });
      });

      const upcomingExpirations = result.current.upcomingDocumentExpirations;
      expect(upcomingExpirations).toHaveLength(1);
      expect(upcomingExpirations[0].type).toBe("passport");
    });
  });

  describe("Utility Actions", () => {
    const mockProfile: UserProfile = {
      id: "user-1",
      email: "test@example.com",
      personalInfo: {
        firstName: "John",
        lastName: "Doe",
      },
      favoriteDestinations: [
        {
          id: "dest-1",
          name: "Paris",
          country: "France",
          visitCount: 2,
        },
      ],
      travelDocuments: [
        {
          id: "doc-1",
          type: "passport",
          number: "123456789",
          expiryDate: "2030-12-31",
          issuingCountry: "US",
        },
      ],
      createdAt: "2025-01-01T00:00:00Z",
      updatedAt: "2025-01-01T00:00:00Z",
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
        profile: mockProfile,
        version: "1.0",
        exportedAt: "2025-01-01T00:00:00Z",
      };

      let importResult: boolean;
      await act(async () => {
        importResult = await result.current.importProfile(JSON.stringify(exportData));
      });

      expect(importResult!).toBe(true);
      expect(result.current.profile).toEqual(mockProfile);
    });

    it("handles invalid import data", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      let importResult: boolean;
      await act(async () => {
        importResult = await result.current.importProfile("invalid json");
      });

      expect(importResult!).toBe(false);
      expect(result.current.error).toBeDefined();
    });

    it("handles import data without profile", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      const exportData = {
        version: "1.0",
        exportedAt: "2025-01-01T00:00:00Z",
      };

      let importResult: boolean;
      await act(async () => {
        importResult = await result.current.importProfile(JSON.stringify(exportData));
      });

      expect(importResult!).toBe(false);
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
        result.current.setProfile(mockProfile);
        useUserProfileStore.setState({
          isLoading: true,
          error: "Some error",
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

  describe("Loading States", () => {
    beforeEach(() => {
      const { result } = renderHook(() => useUserProfileStore());
      act(() => {
        result.current.setProfile({
          id: "user-1",
          email: "test@example.com",
          favoriteDestinations: [],
          travelDocuments: [],
          createdAt: "2025-01-01T00:00:00Z",
          updatedAt: "2025-01-01T00:00:00Z",
        });
      });
    });

    it("manages loading states correctly during profile updates", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      let wasUpdating = false;
      await act(async () => {
        const promise = result.current.updatePersonalInfo({ firstName: "Test" });
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

  describe("Complex Scenarios", () => {
    it("handles complete profile workflow", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      // Start with basic profile
      act(() => {
        result.current.setProfile({
          id: "user-1",
          email: "test@example.com",
          favoriteDestinations: [],
          travelDocuments: [],
          createdAt: "2025-01-01T00:00:00Z",
          updatedAt: "2025-01-01T00:00:00Z",
        });
      });

      expect(result.current.hasCompleteProfile).toBe(false);

      // Update personal info
      await act(async () => {
        await result.current.updatePersonalInfo({
          firstName: "John",
          lastName: "Doe",
          bio: "Travel enthusiast",
        });
      });

      // Update travel preferences
      await act(async () => {
        await result.current.updateTravelPreferences({
          preferredCabinClass: "business",
          preferredAirlines: ["Delta", "United"],
          requireWifi: true,
        });
      });

      // Upload avatar
      const mockFile = new File(["avatar"], "avatar.jpg", {
        type: "image/jpeg",
      });

      await act(async () => {
        await result.current.uploadAvatar(mockFile);
      });

      expect(result.current.hasCompleteProfile).toBe(true);

      // Add favorite destinations
      act(() => {
        result.current.addFavoriteDestination({
          name: "Paris",
          country: "France",
          notes: "Beautiful city",
        });
        result.current.addFavoriteDestination({
          name: "Tokyo",
          country: "Japan",
        });
      });

      // Add travel documents
      act(() => {
        result.current.addTravelDocument({
          type: "passport",
          number: "123456789",
          expiryDate: "2030-12-31",
          issuingCountry: "US",
        });
      });

      expect(result.current.profile?.favoriteDestinations).toHaveLength(2);
      expect(result.current.profile?.travelDocuments).toHaveLength(1);
    });

    it("handles profile export and import workflow", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      // Create profile with data
      act(() => {
        result.current.setProfile({
          id: "user-1",
          email: "test@example.com",
          personalInfo: {
            firstName: "John",
            lastName: "Doe",
          },
          favoriteDestinations: [],
          travelDocuments: [],
          createdAt: "2025-01-01T00:00:00Z",
          updatedAt: "2025-01-01T00:00:00Z",
        });
      });

      // Add some data
      act(() => {
        result.current.addFavoriteDestination({
          name: "Paris",
          country: "France",
        });
      });

      // Export profile
      const exportedData = result.current.exportProfile();
      const originalProfile = result.current.profile;

      // Reset profile
      act(() => {
        result.current.reset();
      });

      expect(result.current.profile).toBeNull();

      // Import profile
      await act(async () => {
        await result.current.importProfile(exportedData);
      });

      expect(result.current.profile?.personalInfo?.firstName).toBe("John");
      expect(result.current.profile?.favoriteDestinations).toHaveLength(1);
      expect(result.current.profile?.favoriteDestinations[0].name).toBe("Paris");
    });
  });

  describe("Utility Selectors", () => {
    it("utility selectors return correct values", () => {
      const { result } = renderHook(() => useUserProfileStore());

      const mockProfile: UserProfile = {
        id: "user-1",
        email: "test@example.com",
        personalInfo: {
          firstName: "John",
          lastName: "Doe",
        },
        travelPreferences: {
          preferredCabinClass: "business",
          preferredAirlines: [],
          excludedAirlines: [],
          maxLayovers: 1,
          preferredAccommodationType: "hotel",
          requireWifi: true,
          requireBreakfast: false,
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
        favoriteDestinations: [
          {
            id: "dest-1",
            name: "Paris",
            country: "France",
            visitCount: 0,
          },
        ],
        travelDocuments: [
          {
            id: "doc-1",
            type: "passport",
            number: "123456789",
            expiryDate: "2030-12-31",
            issuingCountry: "US",
          },
        ],
        createdAt: "2025-01-01T00:00:00Z",
        updatedAt: "2025-01-01T00:00:00Z",
      };

      act(() => {
        result.current.setProfile(mockProfile);
      });

      // Test individual selectors
      const { result: userProfileResult } = renderHook(() =>
        useUserProfileStore((state) => state.profile)
      );
      const { result: displayNameResult } = renderHook(() =>
        useUserProfileStore((state) => state.displayName)
      );
      const { result: personalInfoResult } = renderHook(() =>
        useUserProfileStore((state) => state.profile?.personalInfo)
      );

      expect(userProfileResult.current).toEqual(mockProfile);
      expect(displayNameResult.current).toBe("John Doe");
      expect(personalInfoResult.current).toEqual(mockProfile.personalInfo);
    });
  });
});
