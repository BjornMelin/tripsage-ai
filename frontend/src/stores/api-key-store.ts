import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ApiKey } from "@/types/api-keys";

interface ApiKeyState {
  supportedServices: string[];
  keys: Record<string, ApiKey>;
  selectedService: string | null;

  // Actions
  setSupportedServices: (services: string[]) => void;
  setKeys: (keys: Record<string, ApiKey>) => void;
  setSelectedService: (service: string | null) => void;
  updateKey: (service: string, keyData: Partial<ApiKey>) => void;
  removeKey: (service: string) => void;
}

export const useApiKeyStore = create<ApiKeyState>()(
  persist(
    (set) => ({
      supportedServices: [],
      keys: {},
      selectedService: null,

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
    }),
    {
      name: "api-key-storage",
      // Only persist supportedServices, not the actual keys for security
      partialize: (state) => ({ supportedServices: state.supportedServices }),
    }
  )
);
