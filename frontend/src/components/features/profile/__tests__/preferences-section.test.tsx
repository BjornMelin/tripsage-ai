import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "@/components/ui/use-toast";
import { useCurrencyStore } from "@/stores/currency-store";
import { useUserProfileStore } from "@/stores/user-store";
import { PreferencesSection } from "../preferences-section";

// Mock the stores and hooks
vi.mock("@/stores/user-store");
vi.mock("@/stores/currency-store");
vi.mock("@/components/ui/use-toast");

const mockUser = {
  id: "1",
  email: "test@example.com",
  preferences: {
    language: "en",
    timezone: "America/New_York",
    theme: "system" as const,
    units: "metric" as const,
    dateFormat: "MM/DD/YYYY" as const,
    timeFormat: "12h" as const,
    autoSaveSearches: true,
    smartSuggestions: true,
    locationServices: false,
    analytics: true,
  },
};

const mockUpdateUser = vi.fn();
const mockSetCurrency = vi.fn();
const mockToast = vi.fn();

describe("PreferencesSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useUserProfileStore as any).mockReturnValue({
      user: mockUser,
      updateUser: mockUpdateUser,
    });
    (useCurrencyStore as any).mockReturnValue({
      currency: "USD",
      setCurrency: mockSetCurrency,
    });
    (toast as any).mockImplementation(mockToast);
  });

  it("renders regional & language settings", () => {
    render(<PreferencesSection />);

    expect(screen.getByText("Regional & Language")).toBeInTheDocument();
    expect(screen.getByText("Language")).toBeInTheDocument();
    expect(screen.getByText("Currency")).toBeInTheDocument();
    expect(screen.getByText("Timezone")).toBeInTheDocument();
  });

  it("renders form with default values", () => {
    render(<PreferencesSection />);

    // Check that form is populated with user preferences
    expect(screen.getByDisplayValue("en")).toBeInTheDocument();
    expect(screen.getByDisplayValue("USD")).toBeInTheDocument();
  });

  it("submits form with updated preferences", async () => {
    render(<PreferencesSection />);

    const saveButton = screen.getByRole("button", {
      name: /save preferences/i,
    });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockUpdateUser).toHaveBeenCalledWith({
        preferences: expect.objectContaining({
          language: "en",
          timezone: "America/New_York",
          theme: "system",
          units: "metric",
          dateFormat: "MM/DD/YYYY",
          timeFormat: "12h",
        }),
      });
    });

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "Preferences updated",
        description: "Your preferences have been successfully saved.",
      });
    });
  });

  it("updates currency store when currency changes", async () => {
    render(<PreferencesSection />);

    // Find and change currency select
    const currencySelect = screen.getByDisplayValue("USD");
    fireEvent.change(currencySelect, { target: { value: "EUR" } });

    const saveButton = screen.getByRole("button", {
      name: /save preferences/i,
    });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockSetCurrency).toHaveBeenCalledWith("EUR");
    });
  });

  it("handles form submission error", async () => {
    mockUpdateUser.mockRejectedValueOnce(new Error("Network error"));

    render(<PreferencesSection />);

    const saveButton = screen.getByRole("button", {
      name: /save preferences/i,
    });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "Error",
        description: "Failed to update preferences. Please try again.",
        variant: "destructive",
      });
    });
  });

  it("renders advanced settings section", () => {
    render(<PreferencesSection />);

    expect(screen.getByText("Additional Settings")).toBeInTheDocument();
    expect(screen.getByText("Auto-save Searches")).toBeInTheDocument();
    expect(screen.getByText("Smart Suggestions")).toBeInTheDocument();
    expect(screen.getByText("Location Services")).toBeInTheDocument();
    expect(screen.getByText("Analytics")).toBeInTheDocument();
  });

  it("toggles advanced settings", async () => {
    render(<PreferencesSection />);

    // Find the first switch (Auto-save Searches)
    const switches = screen.getAllByRole("switch");
    const autoSaveSwitch = switches[0];

    fireEvent.click(autoSaveSwitch);

    await waitFor(() => {
      expect(mockUpdateUser).toHaveBeenCalledWith({
        preferences: {
          ...mockUser.preferences,
          autoSaveSearches: false, // Should be toggled
        },
      });
    });

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "Setting updated",
        description: "autoSaveSearches disabled.",
      });
    });
  });

  it("handles advanced setting toggle error", async () => {
    mockUpdateUser.mockRejectedValueOnce(new Error("Network error"));

    render(<PreferencesSection />);

    const switches = screen.getAllByRole("switch");
    const smartSuggestionsSwitch = switches[1]; // Smart Suggestions

    fireEvent.click(smartSuggestionsSwitch);

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "Error",
        description: "Failed to update setting.",
        variant: "destructive",
      });
    });
  });

  it("renders language options correctly", () => {
    render(<PreferencesSection />);

    const languageSelect = screen.getByDisplayValue("en");
    fireEvent.click(languageSelect);

    // Check that language options are available
    expect(screen.getByText("English")).toBeInTheDocument();
    expect(screen.getByText("Español")).toBeInTheDocument();
    expect(screen.getByText("Français")).toBeInTheDocument();
  });

  it("renders currency options correctly", () => {
    render(<PreferencesSection />);

    const currencySelect = screen.getByDisplayValue("USD");
    fireEvent.click(currencySelect);

    // Check that currency options are available
    expect(screen.getByText("$ US Dollar (USD)")).toBeInTheDocument();
    expect(screen.getByText("€ Euro (EUR)")).toBeInTheDocument();
    expect(screen.getByText("£ British Pound (GBP)")).toBeInTheDocument();
  });

  it("renders timezone options correctly", () => {
    render(<PreferencesSection />);

    const timezoneSelect = screen.getByDisplayValue("America/New_York");
    fireEvent.click(timezoneSelect);

    // Check that timezone options are available (they replace underscores with spaces)
    expect(screen.getByText("America/New York")).toBeInTheDocument();
    expect(screen.getByText("Europe/London")).toBeInTheDocument();
    expect(screen.getByText("Asia/Tokyo")).toBeInTheDocument();
  });

  it("validates form fields are required", async () => {
    render(<PreferencesSection />);

    // Try to clear a required field
    const languageSelect = screen.getByDisplayValue("en");
    fireEvent.change(languageSelect, { target: { value: "" } });

    const saveButton = screen.getByRole("button", {
      name: /save preferences/i,
    });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText("Please select a language")).toBeInTheDocument();
    });
  });

  it("shows loading state during form submission", async () => {
    render(<PreferencesSection />);

    const saveButton = screen.getByRole("button", {
      name: /save preferences/i,
    });
    fireEvent.click(saveButton);

    // Check for loading text
    expect(screen.getByText("Saving...")).toBeInTheDocument();
  });

  it("handles missing user preferences gracefully", () => {
    (useUserProfileStore as any).mockReturnValue({
      user: { ...mockUser, preferences: undefined },
      updateUser: mockUpdateUser,
    });

    render(<PreferencesSection />);

    // Should still render with default values
    expect(screen.getByText("Regional & Language")).toBeInTheDocument();
    expect(screen.getByText("Additional Settings")).toBeInTheDocument();
  });

  it("handles missing currency store gracefully", () => {
    (useCurrencyStore as any).mockReturnValue({
      currency: null,
      setCurrency: mockSetCurrency,
    });

    render(<PreferencesSection />);

    // Should still render with USD as default
    expect(screen.getByDisplayValue("USD")).toBeInTheDocument();
  });

  it("toggles each advanced setting independently", async () => {
    render(<PreferencesSection />);

    const switches = screen.getAllByRole("switch");

    // Test each switch
    const settings = [
      "autoSaveSearches",
      "smartSuggestions",
      "locationServices",
      "analytics",
    ];

    for (let i = 0; i < settings.length; i++) {
      const setting = settings[i];
      const expectedValue =
        !mockUser.preferences[setting as keyof typeof mockUser.preferences];

      fireEvent.click(switches[i]);

      await waitFor(() => {
        expect(mockUpdateUser).toHaveBeenCalledWith({
          preferences: {
            ...mockUser.preferences,
            [setting]: expectedValue,
          },
        });
      });

      vi.clearAllMocks(); // Clear mocks between tests
    }
  });
});
