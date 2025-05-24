import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ApiKey } from "@/types/api-keys";

interface AuthState {
  isAuthenticated: boolean;
  userId: string | null;
  token: string | null;
  isApiKeyValid: boolean;
  authError: string | null;
}

interface ApiKeyState extends AuthState {
  supportedServices: string[];
  keys: Record<string, ApiKey>;
  selectedService: string | null;

  // Auth Actions
  setAuthenticated: (isAuth: boolean, userId?: string, token?: string) => void;
  setApiKeyValid: (isValid: boolean) => void;
  setAuthError: (error: string | null) => void;
  logout: () => void;

  // API Key Actions
  setSupportedServices: (services: string[]) => void;
  setKeys: (keys: Record<string, ApiKey>) => void;
  setSelectedService: (service: string | null) => void;
  updateKey: (service: string, keyData: Partial<ApiKey>) => void;
  removeKey: (service: string) => void;
  validateKey: (service: string) => Promise<boolean>;
  loadKeys: () => Promise<void>;
}

export const useApiKeyStore = create<ApiKeyState>()(
  persist(
    (set, get) => ({
      // Auth state
      isAuthenticated: false,
      userId: null,
      token: null,
      isApiKeyValid: false,
      authError: null,

      // API Key state
      supportedServices: [],
      keys: {},
      selectedService: null,

      // Auth Actions
      setAuthenticated: (isAuth, userId, token) =>
        set({
          isAuthenticated: isAuth,
          userId: userId || null,
          token: token || null,
          authError: null,
        }),

      setApiKeyValid: (isValid) => set({ isApiKeyValid: isValid }),

      setAuthError: (error) => set({ authError: error }),

      logout: () =>
        set({
          isAuthenticated: false,
          userId: null,
          token: null,
          isApiKeyValid: false,
          authError: null,
          keys: {},
          selectedService: null,
        }),

      // API Key Actions
      setSupportedServices: (services) => set({ supportedServices: services }),

      setKeys: (keys) => set({ keys }),

      setSelectedService: (service) => set({ selectedService: service }),

      updateKey: (service, keyData) =>
        set((state) => ({
          keys: {
            ...state.keys,
            [service]: {
              ...state.keys[service],
              ...keyData,
            },
          },
        })),

      removeKey: (service) =>
        set((state) => {
          const newKeys = { ...state.keys };
          delete newKeys[service];
          return { keys: newKeys };
        }),

      validateKey: async (service) => {
        const state = get();
        const key = state.keys[service];
        if (!key || !key.api_key) {
          set({ authError: `No API key found for ${service}` });
          return false;
        }

        try {
          const response = await fetch("/api/keys/validate", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(state.token && { Authorization: `Bearer ${state.token}` }),
            },
            body: JSON.stringify({
              service,
              api_key: key.api_key,
              save: false,
            }),
          });

          if (!response.ok) {
            const error = await response.text();
            set({ authError: error, isApiKeyValid: false });
            return false;
          }

          const result = await response.json();
          const isValid = result.is_valid;
          set({
            isApiKeyValid: isValid,
            authError: isValid ? null : result.message,
          });
          return isValid;
        } catch (error) {
          const message =
            error instanceof Error ? error.message : "Validation failed";
          set({ authError: message, isApiKeyValid: false });
          return false;
        }
      },

      loadKeys: async () => {
        const state = get();
        if (!state.isAuthenticated || !state.token) {
          return;
        }

        try {
          const response = await fetch("/api/keys", {
            headers: {
              Authorization: `Bearer ${state.token}`,
            },
          });

          if (!response.ok) {
            throw new Error("Failed to load keys");
          }

          const data = await response.json();
          set({
            keys: data.keys,
            supportedServices: data.supported_services,
          });
        } catch (error) {
          const message =
            error instanceof Error ? error.message : "Failed to load keys";
          set({ authError: message });
        }
      },
    }),
    {
      name: "api-key-storage",
      // Only persist supportedServices and auth state, not the actual keys for security
      partialize: (state) => ({
        supportedServices: state.supportedServices,
        isAuthenticated: state.isAuthenticated,
        userId: state.userId,
        token: state.token,
      }),
    }
  )
);
