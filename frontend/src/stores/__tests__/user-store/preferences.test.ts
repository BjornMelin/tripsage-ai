import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type { TravelDocument } from "@/stores/user-store";
import { useUserProfileStore } from "@/stores/user-store";
import { resetUserProfileStore, setupUserProfileStoreTests } from "./_shared";

setupUserProfileStoreTests();

describe("User Profile Store - Preferences", () => {
  beforeEach(() => {
    resetUserProfileStore();
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
});
