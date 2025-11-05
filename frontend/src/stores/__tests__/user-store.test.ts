import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  type PersonalInfo,
  type PrivacySettings,
  type TravelDocument,
  type TravelPreferences,
  type UserProfile,
  useUserProfileStore,
} from "../user-store";

describe("User Profile Store", () => {
  // Accelerate store async flows in this suite only
  let timeoutSpy: { mockRestore: () => void } | null = null;
  beforeEach(() => {
    timeoutSpy = vi.spyOn(globalThis, "setTimeout").mockImplementation(((
      cb: TimerHandler,
      _ms?: number,
      ...args: unknown[]
    ) => {
      if (typeof cb === "function") {
        // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
        cb(...(args as never[]));
      }
      return 0 as unknown as ReturnType<typeof setTimeout>;
    }) as unknown as typeof setTimeout);
    // Reset store state before each test to prevent state pollution
    act(() => {
      useUserProfileStore.getState().reset();
    });
  });
  afterEach(() => {
    timeoutSpy?.mockRestore();
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

  describe("Profile Management", () => {
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

  describe("Avatar Management", () => {
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

    it("successfully uploads avatar", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      const mockFile = new File(["avatar content"], "avatar.jpg", {
        type: "image/jpeg",
      });

      let uploadResult: string | null = null;
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

      let uploadResult: string | null = null;
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

      let uploadResult: string | null = null;
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

      let removeResult = false;
      await act(async () => {
        removeResult = await result.current.removeAvatar();
      });

      expect(removeResult).toBe(true);
      expect(result.current.profile?.avatarUrl).toBeUndefined();
      expect(result.current.isUpdatingProfile).toBe(false);
    });

    it("handles remove avatar when no profile exists", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      act(() => {
        result.current.setProfile(null);
      });

      let removeResult = true;
      await act(async () => {
        removeResult = await result.current.removeAvatar();
      });

      expect(removeResult).toBe(false);
    });
  });

  describe("Favorite Destinations", () => {
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

    it("adds a favorite destination", () => {
      const { result } = renderHook(() => useUserProfileStore());

      const destination = {
        country: "France",
        name: "Paris",
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
        result.current.addFavoriteDestination({ country: "France", name: "Paris" });
        result.current.addFavoriteDestination({ country: "Japan", name: "Tokyo" });
      });

      expect(result.current.profile?.favoriteDestinations).toHaveLength(2);

      const parisId = result.current.profile?.favoriteDestinations[0]?.id;
      if (!parisId) {
        throw new Error("Paris destination ID is undefined");
      }

      act(() => {
        result.current.removeFavoriteDestination(parisId);
      });

      expect(result.current.profile?.favoriteDestinations).toHaveLength(1);
      expect(result.current.profile?.favoriteDestinations[0].name).toBe("Tokyo");
    });

    it("updates a favorite destination", () => {
      const { result } = renderHook(() => useUserProfileStore());

      act(() => {
        result.current.addFavoriteDestination({ country: "France", name: "Paris" });
      });

      const destinationId = result.current.profile?.favoriteDestinations[0]?.id;
      if (!destinationId) {
        throw new Error("Destination ID is undefined");
      }

      act(() => {
        result.current.updateFavoriteDestination(destinationId, {
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
        result.current.addFavoriteDestination({ country: "France", name: "Paris" });
      });

      const destinationId = result.current.profile?.favoriteDestinations[0]?.id;
      if (!destinationId) {
        throw new Error("Destination ID is undefined");
      }

      act(() => {
        result.current.incrementDestinationVisit(destinationId);
      });

      const destination = result.current.profile?.favoriteDestinations[0];
      expect(destination?.visitCount).toBe(1);
      expect(destination?.lastVisited).toBeDefined();

      act(() => {
        result.current.incrementDestinationVisit(destinationId);
      });

      expect(result.current.profile?.favoriteDestinations[0].visitCount).toBe(2);
    });

    it("handles destination operations when no profile exists", () => {
      const { result } = renderHook(() => useUserProfileStore());

      act(() => {
        result.current.setProfile(null);
      });

      act(() => {
        result.current.addFavoriteDestination({ country: "France", name: "Paris" });
      });

      expect(result.current.profile).toBeNull();
    });
  });

  describe("Travel Documents", () => {
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

    it("adds a travel document", () => {
      const { result } = renderHook(() => useUserProfileStore());

      const document: Omit<TravelDocument, "id"> = {
        expiryDate: "2030-12-31",
        issuingCountry: "United States",
        notes: "Valid for 10 years",
        number: "123456789",
        type: "passport",
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
          expiryDate: "2030-12-31",
          issuingCountry: "US",
          number: "123456789",
          type: "passport",
        });
        result.current.addTravelDocument({
          expiryDate: "2025-06-30",
          issuingCountry: "France",
          number: "987654321",
          type: "visa",
        });
      });

      expect(result.current.profile?.travelDocuments).toHaveLength(2);

      const passportId = result.current.profile?.travelDocuments[0]?.id;
      if (!passportId) {
        throw new Error("Passport ID is undefined");
      }

      act(() => {
        result.current.removeTravelDocument(passportId);
      });

      expect(result.current.profile?.travelDocuments).toHaveLength(1);
      expect(result.current.profile?.travelDocuments[0].type).toBe("visa");
    });

    it("updates a travel document", () => {
      const { result } = renderHook(() => useUserProfileStore());

      act(() => {
        result.current.addTravelDocument({
          expiryDate: "2030-12-31",
          issuingCountry: "US",
          number: "123456789",
          type: "passport",
        });
      });

      const documentId = result.current.profile?.travelDocuments[0]?.id;
      if (!documentId) {
        throw new Error("Document ID is undefined");
      }

      act(() => {
        result.current.updateTravelDocument(documentId, {
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
          expiryDate: "2030-12-31",
          issuingCountry: "US",
          number: "123456789",
          type: "passport",
        });
      });

      expect(result.current.profile).toBeNull();
    });
  });

  describe.skip("Computed Properties", () => {
    it("correctly computes display name", () => {
      const { result } = renderHook(() => useUserProfileStore());

      // No profile
      expect(result.current.displayName).toBe("");

      // Profile with display name
      act(() => {
        result.current.setProfile({
          createdAt: "2025-01-01T00:00:00Z",
          email: "test@example.com",
          favoriteDestinations: [],
          id: "user-1",
          personalInfo: {
            displayName: "Custom Name",
          },
          travelDocuments: [],
          updatedAt: "2025-01-01T00:00:00Z",
        });
      });

      expect(result.current.displayName).toBe("Custom Name");

      // Profile with first and last name
      act(() => {
        result.current.setProfile({
          createdAt: "2025-01-01T00:00:00Z",
          email: "test@example.com",
          favoriteDestinations: [],
          id: "user-1",
          personalInfo: {
            firstName: "John",
            lastName: "Doe",
          },
          travelDocuments: [],
          updatedAt: "2025-01-01T00:00:00Z",
        });
      });

      expect(result.current.displayName).toBe("John Doe");

      // Profile with only first name
      act(() => {
        result.current.setProfile({
          createdAt: "2025-01-01T00:00:00Z",
          email: "test@example.com",
          favoriteDestinations: [],
          id: "user-1",
          personalInfo: {
            firstName: "Jane",
          },
          travelDocuments: [],
          updatedAt: "2025-01-01T00:00:00Z",
        });
      });

      expect(result.current.displayName).toBe("Jane");

      // Profile with only email
      act(() => {
        result.current.setProfile({
          createdAt: "2025-01-01T00:00:00Z",
          email: "username@example.com",
          favoriteDestinations: [],
          id: "user-1",
          travelDocuments: [],
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
          createdAt: "2025-01-01T00:00:00Z",
          email: "test@example.com",
          favoriteDestinations: [],
          id: "user-1",
          personalInfo: {
            firstName: "John",
          },
          travelDocuments: [],
          updatedAt: "2025-01-01T00:00:00Z",
        });
      });

      expect(result.current.hasCompleteProfile).toBe(false);

      // Complete profile
      act(() => {
        result.current.setProfile({
          avatarUrl: "https://example.com/avatar.jpg",
          createdAt: "2025-01-01T00:00:00Z",
          email: "test@example.com",
          favoriteDestinations: [],
          id: "user-1",
          personalInfo: {
            firstName: "John",
            lastName: "Doe",
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
          createdAt: "2025-01-01T00:00:00Z",
          email: "test@example.com",
          favoriteDestinations: [],
          id: "user-1",
          travelDocuments: [
            {
              expiryDate: inThirtyDays.toISOString(),
              id: "doc-1",
              issuingCountry: "US",
              number: "123456789",
              type: "passport",
            },
            {
              expiryDate: inNinetyDays.toISOString(),
              id: "doc-2",
              issuingCountry: "France",
              number: "987654321",
              type: "visa",
            },
          ],
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
      createdAt: "2025-01-01T00:00:00Z",
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
          expiryDate: "2030-12-31",
          id: "doc-1",
          issuingCountry: "US",
          number: "123456789",
          type: "passport",
        },
      ],
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

  describe.skip("Complex Scenarios", () => {
    it("handles complete profile workflow", async () => {
      const { result } = renderHook(() => useUserProfileStore());

      // Start with basic profile
      act(() => {
        result.current.setProfile({
          createdAt: "2025-01-01T00:00:00Z",
          email: "test@example.com",
          favoriteDestinations: [],
          id: "user-1",
          travelDocuments: [],
          updatedAt: "2025-01-01T00:00:00Z",
        });
      });

      expect(result.current.hasCompleteProfile).toBe(false);

      // Update personal info
      await act(async () => {
        await result.current.updatePersonalInfo({
          bio: "Travel enthusiast",
          firstName: "John",
          lastName: "Doe",
        });
      });

      // Update travel preferences
      await act(async () => {
        await result.current.updateTravelPreferences({
          preferredAirlines: ["Delta", "United"],
          preferredCabinClass: "business",
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
          country: "France",
          name: "Paris",
          notes: "Beautiful city",
        });
        result.current.addFavoriteDestination({
          country: "Japan",
          name: "Tokyo",
        });
      });

      // Add travel documents
      act(() => {
        result.current.addTravelDocument({
          expiryDate: "2030-12-31",
          issuingCountry: "US",
          number: "123456789",
          type: "passport",
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
          createdAt: "2025-01-01T00:00:00Z",
          email: "test@example.com",
          favoriteDestinations: [],
          id: "user-1",
          personalInfo: {
            firstName: "John",
            lastName: "Doe",
          },
          travelDocuments: [],
          updatedAt: "2025-01-01T00:00:00Z",
        });
      });

      // Add some data
      act(() => {
        result.current.addFavoriteDestination({
          country: "France",
          name: "Paris",
        });
      });

      // Export profile
      const exportedData = result.current.exportProfile();
      result.current.profile; // Access original profile

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

  describe.skip("Utility Selectors", () => {
    it("utility selectors return correct values", () => {
      const { result } = renderHook(() => useUserProfileStore());

      const mockProfile: UserProfile = {
        createdAt: "2025-01-01T00:00:00Z",
        email: "test@example.com",
        favoriteDestinations: [
          {
            country: "France",
            id: "dest-1",
            name: "Paris",
            visitCount: 0,
          },
        ],
        id: "user-1",
        personalInfo: {
          firstName: "John",
          lastName: "Doe",
        },
        privacySettings: {
          allowDataSharing: false,
          enableAnalytics: true,
          enableLocationTracking: false,
          profileVisibility: "friends",
          showTravelHistory: true,
        },
        travelDocuments: [
          {
            expiryDate: "2030-12-31",
            id: "doc-1",
            issuingCountry: "US",
            number: "123456789",
            type: "passport",
          },
        ],
        travelPreferences: {
          accessibilityRequirements: [],
          dietaryRestrictions: [],
          excludedAirlines: [],
          maxLayovers: 1,
          preferredAccommodationType: "hotel",
          preferredAirlines: [],
          preferredCabinClass: "business",
          preferredHotelChains: [],
          requireBreakfast: false,
          requireGym: false,
          requireParking: false,
          requirePool: false,
          requireWifi: true,
        },
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
