import { z } from "zod";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

// Validation schemas for user profile
const TravelPreferencesSchema = z.object({
  preferredCabinClass: z
    .enum(["economy", "premium_economy", "business", "first"])
    .default("economy"),
  preferredAirlines: z.array(z.string()).default([]),
  excludedAirlines: z.array(z.string()).default([]),
  maxLayovers: z.number().min(0).max(5).default(2),
  preferredDepartureTime: z
    .enum(["early_morning", "morning", "afternoon", "evening", "late_night"])
    .optional(),
  preferredArrivalTime: z
    .enum(["early_morning", "morning", "afternoon", "evening", "late_night"])
    .optional(),
  preferredAccommodationType: z
    .enum(["hotel", "apartment", "villa", "hostel", "resort"])
    .default("hotel"),
  maxBudgetPerNight: z.number().min(0).optional(),
  preferredHotelChains: z.array(z.string()).default([]),
  requireWifi: z.boolean().default(true),
  requireBreakfast: z.boolean().default(false),
  requireParking: z.boolean().default(false),
  requireGym: z.boolean().default(false),
  requirePool: z.boolean().default(false),
  accessibilityRequirements: z.array(z.string()).default([]),
  dietaryRestrictions: z.array(z.string()).default([]),
});

const PersonalInfoSchema = z.object({
  firstName: z.string().optional(),
  lastName: z.string().optional(),
  displayName: z.string().optional(),
  bio: z.string().max(500).optional(),
  location: z.string().optional(),
  website: z.string().url().optional(),
  phoneNumber: z.string().optional(),
  dateOfBirth: z.string().optional(),
  gender: z.enum(["male", "female", "other", "prefer_not_to_say"]).optional(),
  emergencyContact: z
    .object({
      name: z.string(),
      phone: z.string(),
      email: z.string().email(),
      relationship: z.string(),
    })
    .optional(),
});

const PrivacySettingsSchema = z.object({
  profileVisibility: z.enum(["public", "friends", "private"]).default("private"),
  showTravelHistory: z.boolean().default(false),
  allowDataSharing: z.boolean().default(false),
  enableAnalytics: z.boolean().default(true),
  enableLocationTracking: z.boolean().default(false),
});

export const UserProfileSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  avatarUrl: z.string().url().optional(),
  personalInfo: PersonalInfoSchema.optional(),
  travelPreferences: TravelPreferencesSchema.optional(),
  privacySettings: PrivacySettingsSchema.optional(),
  favoriteDestinations: z
    .array(
      z.object({
        id: z.string(),
        name: z.string(),
        country: z.string(),
        notes: z.string().optional(),
        visitCount: z.number().default(0),
        lastVisited: z.string().optional(),
      })
    )
    .default([]),
  travelDocuments: z
    .array(
      z.object({
        id: z.string(),
        type: z.enum(["passport", "visa", "license", "insurance", "vaccination"]),
        number: z.string(),
        expiryDate: z.string(),
        issuingCountry: z.string(),
        notes: z.string().optional(),
      })
    )
    .default([]),
  createdAt: z.string(),
  updatedAt: z.string(),
});

// Types derived from schemas
export type TravelPreferences = z.infer<typeof TravelPreferencesSchema>;
export type PersonalInfo = z.infer<typeof PersonalInfoSchema>;
export type PrivacySettings = z.infer<typeof PrivacySettingsSchema>;
export type UserProfile = z.infer<typeof UserProfileSchema>;
export type FavoriteDestination = UserProfile["favoriteDestinations"][0];
export type TravelDocument = UserProfile["travelDocuments"][0];

// User profile store interface (authentication is handled by auth-store)
interface UserProfileState {
  // Profile data
  profile: UserProfile | null;

  // Loading states
  isLoading: boolean;
  isUpdatingProfile: boolean;
  isUploadingAvatar: boolean;

  // Error states
  error: string | null;
  uploadError: string | null;

  // Computed properties
  displayName: string;
  hasCompleteProfile: boolean;
  upcomingDocumentExpirations: TravelDocument[];

  // Profile management actions
  setProfile: (profile: UserProfile | null) => void;
  updatePersonalInfo: (info: Partial<PersonalInfo>) => Promise<boolean>;
  updateTravelPreferences: (
    preferences: Partial<TravelPreferences>
  ) => Promise<boolean>;
  updatePrivacySettings: (settings: Partial<PrivacySettings>) => Promise<boolean>;

  // Avatar management
  uploadAvatar: (file: File) => Promise<string | null>;
  removeAvatar: () => Promise<boolean>;

  // Favorite destinations
  addFavoriteDestination: (
    destination: Omit<FavoriteDestination, "id" | "visitCount">
  ) => void;
  removeFavoriteDestination: (destinationId: string) => void;
  updateFavoriteDestination: (
    destinationId: string,
    updates: Partial<FavoriteDestination>
  ) => void;
  incrementDestinationVisit: (destinationId: string) => void;

  // Travel documents
  addTravelDocument: (document: Omit<TravelDocument, "id">) => void;
  removeTravelDocument: (documentId: string) => void;
  updateTravelDocument: (documentId: string, updates: Partial<TravelDocument>) => void;

  // Utility actions
  exportProfile: () => string;
  importProfile: (data: string) => Promise<boolean>;
  clearError: () => void;
  reset: () => void;
}

// Validation schema for the user profile store state
// const userProfileStoreSchema = z.object({ // Future validation
//   profile: UserProfileSchema.nullable(),
//   isLoading: z.boolean(),
//   isUpdatingProfile: z.boolean(),
//   isUploadingAvatar: z.boolean(),
//   error: z.string().nullable(),
//   uploadError: z.string().nullable(),
//   displayName: z.string(),
//   hasCompleteProfile: z.boolean(),
//   upcomingDocumentExpirations: z.array(z.any()), // Could be more specific with TravelDocument schema
// });

// Helper functions
const generateId = () =>
  Date.now().toString(36) + Math.random().toString(36).substring(2, 5);
const getCurrentTimestamp = () => new Date().toISOString();

// Get display name helper
const getDisplayName = (profile: UserProfile | null): string => {
  if (!profile) return "";

  const personalInfo = profile.personalInfo;
  if (personalInfo?.displayName) return personalInfo.displayName;
  if (personalInfo?.firstName && personalInfo?.lastName) {
    return `${personalInfo.firstName} ${personalInfo.lastName}`;
  }
  if (personalInfo?.firstName) return personalInfo.firstName;
  return profile.email.split("@")[0];
};

// Check if profile is complete
const hasCompleteProfile = (profile: UserProfile | null): boolean => {
  if (!profile) return false;

  const personalInfo = profile.personalInfo;
  return !!(
    personalInfo?.firstName &&
    personalInfo?.lastName &&
    profile.travelPreferences &&
    profile.avatarUrl
  );
};

// Get upcoming document expirations (within 60 days)
const getUpcomingDocumentExpirations = (
  profile: UserProfile | null
): TravelDocument[] => {
  if (!profile) return [];

  const now = new Date();
  const sixtyDaysFromNow = new Date(now.getTime() + 60 * 24 * 60 * 60 * 1000);

  return profile.travelDocuments.filter((doc) => {
    const expiryDate = new Date(doc.expiryDate);
    return expiryDate <= sixtyDaysFromNow && expiryDate > now;
  });
};

export const useUserProfileStore = create<UserProfileState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        profile: null,

        // Loading states
        isLoading: false,
        isUpdatingProfile: false,
        isUploadingAvatar: false,

        // Error states
        error: null,
        uploadError: null,

        // Computed properties
        get displayName() {
          return getDisplayName(get().profile);
        },

        get hasCompleteProfile() {
          return hasCompleteProfile(get().profile);
        },

        get upcomingDocumentExpirations() {
          return getUpcomingDocumentExpirations(get().profile);
        },

        // Profile management actions
        setProfile: (profile: UserProfile | null) => {
          set({ profile });
        },

        updatePersonalInfo: async (info: Partial<PersonalInfo>) => {
          const { profile } = get();
          if (!profile) return false;

          set({ isUpdatingProfile: true, error: null });

          try {
            const result = PersonalInfoSchema.safeParse(info);
            if (!result.success) {
              throw new Error("Invalid personal information");
            }

            const updatedProfile = {
              ...profile,
              personalInfo: {
                ...profile.personalInfo,
                ...result.data,
              },
              updatedAt: getCurrentTimestamp(),
            };

            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 500));

            set({
              profile: updatedProfile,
              isUpdatingProfile: false,
            });

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to update personal info";
            set({
              error: message,
              isUpdatingProfile: false,
            });
            return false;
          }
        },

        updateTravelPreferences: async (preferences: Partial<TravelPreferences>) => {
          const { profile } = get();
          if (!profile) return false;

          set({ isUpdatingProfile: true, error: null });

          try {
            const result = TravelPreferencesSchema.safeParse({
              ...profile.travelPreferences,
              ...preferences,
            });

            if (!result.success) {
              throw new Error("Invalid travel preferences");
            }

            const updatedProfile = {
              ...profile,
              travelPreferences: result.data,
              updatedAt: getCurrentTimestamp(),
            };

            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 500));

            set({
              profile: updatedProfile,
              isUpdatingProfile: false,
            });

            return true;
          } catch (error) {
            const message =
              error instanceof Error
                ? error.message
                : "Failed to update travel preferences";
            set({
              error: message,
              isUpdatingProfile: false,
            });
            return false;
          }
        },

        updatePrivacySettings: async (settings: Partial<PrivacySettings>) => {
          const { profile } = get();
          if (!profile) return false;

          set({ isUpdatingProfile: true, error: null });

          try {
            const result = PrivacySettingsSchema.safeParse({
              ...profile.privacySettings,
              ...settings,
            });

            if (!result.success) {
              throw new Error("Invalid privacy settings");
            }

            const updatedProfile = {
              ...profile,
              privacySettings: result.data,
              updatedAt: getCurrentTimestamp(),
            };

            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 500));

            set({
              profile: updatedProfile,
              isUpdatingProfile: false,
            });

            return true;
          } catch (error) {
            const message =
              error instanceof Error
                ? error.message
                : "Failed to update privacy settings";
            set({
              error: message,
              isUpdatingProfile: false,
            });
            return false;
          }
        },

        // Avatar management
        uploadAvatar: async (file: File) => {
          set({ isUploadingAvatar: true, uploadError: null });

          try {
            // Validate file
            if (!file.type.startsWith("image/")) {
              throw new Error("File must be an image");
            }

            if (file.size > 5 * 1024 * 1024) {
              throw new Error("File size must be less than 5MB");
            }

            // Mock upload
            await new Promise((resolve) => setTimeout(resolve, 2000));

            const avatarUrl = `https://example.com/avatars/${generateId()}.${file.type.split("/")[1]}`;

            const { profile } = get();
            if (profile) {
              set({
                profile: {
                  ...profile,
                  avatarUrl,
                  updatedAt: getCurrentTimestamp(),
                },
                isUploadingAvatar: false,
              });
            }

            return avatarUrl;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to upload avatar";
            set({
              uploadError: message,
              isUploadingAvatar: false,
            });
            return null;
          }
        },

        removeAvatar: async () => {
          const { profile } = get();
          if (!profile) return false;

          set({ isUpdatingProfile: true });

          try {
            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 500));

            set({
              profile: {
                ...profile,
                avatarUrl: undefined,
                updatedAt: getCurrentTimestamp(),
              },
              isUpdatingProfile: false,
            });

            return true;
          } catch (_error) {
            set({ isUpdatingProfile: false });
            return false;
          }
        },

        // Favorite destinations
        addFavoriteDestination: (
          destination: Omit<FavoriteDestination, "id" | "visitCount">
        ) => {
          const { profile } = get();
          if (!profile) return;

          const newDestination: FavoriteDestination = {
            ...destination,
            id: generateId(),
            visitCount: 0,
          };

          set({
            profile: {
              ...profile,
              favoriteDestinations: [...profile.favoriteDestinations, newDestination],
              updatedAt: getCurrentTimestamp(),
            },
          });
        },

        removeFavoriteDestination: (destinationId: string) => {
          const { profile } = get();
          if (!profile) return;

          set({
            profile: {
              ...profile,
              favoriteDestinations: profile.favoriteDestinations.filter(
                (d: FavoriteDestination) => d.id !== destinationId
              ),
              updatedAt: getCurrentTimestamp(),
            },
          });
        },

        updateFavoriteDestination: (
          destinationId: string,
          updates: Partial<FavoriteDestination>
        ) => {
          const { profile } = get();
          if (!profile) return;

          set({
            profile: {
              ...profile,
              favoriteDestinations: profile.favoriteDestinations.map(
                (d: FavoriteDestination) =>
                  d.id === destinationId ? { ...d, ...updates } : d
              ),
              updatedAt: getCurrentTimestamp(),
            },
          });
        },

        incrementDestinationVisit: (destinationId: string) => {
          const { profile } = get();
          if (!profile) return;

          const now = getCurrentTimestamp();

          set({
            profile: {
              ...profile,
              favoriteDestinations: profile.favoriteDestinations.map(
                (d: FavoriteDestination) =>
                  d.id === destinationId
                    ? { ...d, visitCount: d.visitCount + 1, lastVisited: now }
                    : d
              ),
              updatedAt: now,
            },
          });
        },

        // Travel documents
        addTravelDocument: (document: Omit<TravelDocument, "id">) => {
          const { profile } = get();
          if (!profile) return;

          const newDocument: TravelDocument = {
            ...document,
            id: generateId(),
          };

          set({
            profile: {
              ...profile,
              travelDocuments: [...profile.travelDocuments, newDocument],
              updatedAt: getCurrentTimestamp(),
            },
          });
        },

        removeTravelDocument: (documentId: string) => {
          const { profile } = get();
          if (!profile) return;

          set({
            profile: {
              ...profile,
              travelDocuments: profile.travelDocuments.filter(
                (d: TravelDocument) => d.id !== documentId
              ),
              updatedAt: getCurrentTimestamp(),
            },
          });
        },

        updateTravelDocument: (
          documentId: string,
          updates: Partial<TravelDocument>
        ) => {
          const { profile } = get();
          if (!profile) return;

          set({
            profile: {
              ...profile,
              travelDocuments: profile.travelDocuments.map((d: TravelDocument) =>
                d.id === documentId ? { ...d, ...updates } : d
              ),
              updatedAt: getCurrentTimestamp(),
            },
          });
        },

        // Utility actions
        exportProfile: () => {
          const { profile } = get();
          if (!profile) return "";

          const exportData = {
            profile,
            exportedAt: getCurrentTimestamp(),
            version: "1.0",
          };

          return JSON.stringify(exportData, null, 2);
        },

        importProfile: async (data: string) => {
          try {
            const importData = JSON.parse(data);

            if (importData.profile) {
              const result = UserProfileSchema.safeParse(importData.profile);
              if (result.success) {
                set({ profile: result.data });
                return true;
              }
              throw new Error("Invalid profile data");
            }

            return false;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to import profile";
            set({ error: message });
            return false;
          }
        },

        clearError: () => {
          set({ error: null, uploadError: null });
        },

        reset: () => {
          set({
            profile: null,
            isLoading: false,
            isUpdatingProfile: false,
            isUploadingAvatar: false,
            error: null,
            uploadError: null,
          });
        },
      }),
      {
        name: "user-profile-storage",
        partialize: (state) => ({
          // Only persist the profile data
          profile: state.profile,
        }),
      }
    ),
    { name: "UserProfileStore" }
  )
);

// Utility selectors for common use cases
export const useUserProfile = () => useUserProfileStore((state) => state.profile);
export const useUserDisplayName = () =>
  useUserProfileStore((state) => state.displayName);
export const useUserPersonalInfo = () =>
  useUserProfileStore((state) => state.profile?.personalInfo);
export const useUserTravelPreferences = () =>
  useUserProfileStore((state) => state.profile?.travelPreferences);
export const useUserPrivacySettings = () =>
  useUserProfileStore((state) => state.profile?.privacySettings);
export const useFavoriteDestinations = () =>
  useUserProfileStore((state) => state.profile?.favoriteDestinations || []);
export const useTravelDocuments = () =>
  useUserProfileStore((state) => state.profile?.travelDocuments || []);
export const useUpcomingDocumentExpirations = () =>
  useUserProfileStore((state) => state.upcomingDocumentExpirations);
export const useHasCompleteProfile = () =>
  useUserProfileStore((state) => state.hasCompleteProfile);
