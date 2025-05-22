import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User {
  id: string;
  email: string;
  displayName?: string;
  firstName?: string;
  lastName?: string;
  avatarUrl?: string;
  isEmailVerified: boolean;
}

interface UserState {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  setUser: (user: User | null) => void;
  updateUser: (data: Partial<User>) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    firstName?: string,
    lastName?: string
  ) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

export const useUserStore = create<UserState>()(
  persist(
    (set, get) => ({
      user: null,
      isLoading: false,
      error: null,

      setUser: (user) => set({ user }),

      updateUser: (data) => {
        const { user } = get();
        if (!user) return;

        set({
          user: { ...user, ...data },
        });
      },

      login: async (email, password) => {
        set({ isLoading: true, error: null });

        try {
          // This will be replaced with actual API call
          await new Promise((resolve) => setTimeout(resolve, 1000));

          // Mock user data
          set({
            user: {
              id: "1",
              email,
              displayName: email.split("@")[0],
              isEmailVerified: true,
            },
            isLoading: false,
          });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Login failed",
            isLoading: false,
          });
        }
      },

      register: async (email, password, firstName, lastName) => {
        set({ isLoading: true, error: null });

        try {
          // This will be replaced with actual API call
          await new Promise((resolve) => setTimeout(resolve, 1000));

          // Mock user data
          set({
            user: {
              id: "1",
              email,
              firstName,
              lastName,
              displayName: firstName
                ? `${firstName} ${lastName || ""}`.trim()
                : email.split("@")[0],
              isEmailVerified: false,
            },
            isLoading: false,
          });
        } catch (error) {
          set({
            error:
              error instanceof Error ? error.message : "Registration failed",
            isLoading: false,
          });
        }
      },

      logout: () => {
        set({ user: null, error: null });
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: "user-storage",
      partialize: (state) => ({ user: state.user }),
    }
  )
);
