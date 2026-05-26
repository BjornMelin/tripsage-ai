/**
 * @fileoverview Preferences section: update currency, language, timezone, and units.
 */

"use client";

import { type PreferencesFormData, preferencesFormSchema } from "@schemas/profile";
import { CURRENCY_CODE_SCHEMA } from "@schemas/shared/money";
import { GlobeIcon, ZapIcon } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/use-toast";
import { useAuthCore } from "@/features/auth/store/auth/auth-core";
import { useCurrencyStore } from "@/features/shared/store/currency-store";
import { useTheme } from "@/hooks/use-theme";
import { useZodForm } from "@/hooks/use-zod-form";
import { getUnknownErrorMessage } from "@/lib/errors/get-unknown-error-message";
import { getBrowserClient } from "@/lib/supabase";

type AdditionalSettingKey =
  | "analytics"
  | "autoSaveSearches"
  | "locationServices"
  | "smartSuggestions";

const ADDITIONAL_SETTING_OPTIONS = [
  {
    description: "Automatically save your search history for quick access.",
    descriptionId: "auto-save-searches-description",
    key: "autoSaveSearches",
    label: "Auto-save Searches",
    labelId: "auto-save-searches-label",
  },
  {
    description: "Get AI-powered travel suggestions based on your preferences.",
    descriptionId: "smart-suggestions-description",
    key: "smartSuggestions",
    label: "Smart Suggestions",
    labelId: "smart-suggestions-label",
  },
  {
    description: "Allow location access for nearby recommendations.",
    descriptionId: "location-services-description",
    key: "locationServices",
    label: "Location Services",
    labelId: "location-services-label",
  },
  {
    description: "Help us improve by sharing anonymous usage data.",
    descriptionId: "analytics-description",
    key: "analytics",
    label: "Analytics",
    labelId: "analytics-label",
  },
] as const satisfies readonly {
  description: string;
  descriptionId: string;
  key: AdditionalSettingKey;
  label: string;
  labelId: string;
}[];

/**
 * Preferences section component.
 * @returns The preferences section component.
 */
export function PreferencesSection() {
  const authUser = useAuthCore((state) => state.user);
  const setUser = useAuthCore((state) => state.setUser);
  const baseCurrency = useCurrencyStore((state) => state.baseCurrency);
  const setBaseCurrency = useCurrencyStore((state) => state.setBaseCurrency);
  const { toast } = useToast();
  const { setTheme } = useTheme();

  const defaultValues = useMemo(
    (): PreferencesFormData => ({
      currency: authUser?.preferences?.currency ?? baseCurrency ?? "USD",
      dateFormat: authUser?.preferences?.dateFormat ?? "MM/DD/YYYY",
      language: authUser?.preferences?.language ?? "en",
      theme: authUser?.preferences?.theme ?? "system",
      timeFormat: authUser?.preferences?.timeFormat ?? "12h",
      timezone:
        authUser?.preferences?.timezone ??
        Intl.DateTimeFormat().resolvedOptions().timeZone,
      units: authUser?.preferences?.units ?? "metric",
    }),
    [authUser?.preferences, baseCurrency]
  );

  const initialAdditionalSettings = useMemo(
    () => ({
      analytics: authUser?.preferences?.analytics ?? true,
      autoSaveSearches: authUser?.preferences?.autoSaveSearches ?? true,
      locationServices: authUser?.preferences?.locationServices ?? false,
      smartSuggestions: authUser?.preferences?.smartSuggestions ?? true,
    }),
    [
      authUser?.preferences?.analytics,
      authUser?.preferences?.autoSaveSearches,
      authUser?.preferences?.locationServices,
      authUser?.preferences?.smartSuggestions,
    ]
  );
  const [additionalSettings, setAdditionalSettings] = useState(
    initialAdditionalSettings
  );

  const form = useZodForm({
    defaultValues,
    mode: "onChange",
    schema: preferencesFormSchema,
  });
  const resetForm = form.reset;

  const didMountRef = useRef(false);

  useEffect(() => {
    if (!didMountRef.current) {
      didMountRef.current = true;
      return;
    }
    resetForm(defaultValues);
  }, [defaultValues, resetForm]);

  useEffect(() => {
    setAdditionalSettings(initialAdditionalSettings);
  }, [initialAdditionalSettings]);

  const onSubmit = async (data: PreferencesFormData) => {
    try {
      if (!authUser) {
        throw new Error("You must be signed in to update your preferences.");
      }

      const supabase = getBrowserClient();
      if (!supabase) {
        throw new Error("Unable to access preferences client. Please try again.");
      }

      const nextPreferences = {
        ...(authUser.preferences ?? {}),
        currency: data.currency,
        dateFormat: data.dateFormat,
        language: data.language,
        theme: data.theme,
        timeFormat: data.timeFormat,
        timezone: data.timezone,
        units: data.units,
      };

      const { data: result, error } = await supabase.auth.updateUser({
        data: {
          preferences: nextPreferences,
        },
      });

      if (error) {
        throw error;
      }

      setUser({
        ...authUser,
        preferences: nextPreferences,
        updatedAt: result.user?.updated_at ?? authUser.updatedAt,
      });

      // Update currency store if changed
      if (data.currency !== baseCurrency) {
        const parsedCurrency = CURRENCY_CODE_SCHEMA.parse(data.currency);
        setBaseCurrency(parsedCurrency);
      }

      setTheme(data.theme);

      toast({
        description: "Your preferences have been successfully saved.",
        title: "Preferences updated",
      });
    } catch (error) {
      toast({
        description: getUnknownErrorMessage(
          error,
          "Failed to update preferences. Please try again."
        ),
        title: "Error",
        variant: "destructive",
      });
    }
  };

  const toggleAdditionalSetting = async (
    setting: AdditionalSettingKey,
    enabled: boolean
  ) => {
    const settingLabel =
      ADDITIONAL_SETTING_OPTIONS.find((option) => option.key === setting)?.label ??
      setting;

    setAdditionalSettings((prev) => ({ ...prev, [setting]: enabled }));

    try {
      if (!authUser) {
        throw new Error("You must be signed in to update your preferences.");
      }

      const supabase = getBrowserClient();
      if (!supabase) {
        throw new Error("Unable to access preferences client. Please try again.");
      }

      const nextPreferences = {
        ...(authUser.preferences ?? {}),
        [setting]: enabled,
      };

      const { data, error } = await supabase.auth.updateUser({
        data: {
          preferences: nextPreferences,
        },
      });

      if (error) {
        throw error;
      }

      setUser({
        ...authUser,
        preferences: nextPreferences,
        updatedAt: data.user?.updated_at ?? authUser.updatedAt,
      });

      toast({
        description: `${settingLabel} ${enabled ? "enabled" : "disabled"}.`,
        title: "Setting updated",
      });
    } catch (error) {
      setAdditionalSettings((prev) => ({ ...prev, [setting]: !enabled }));
      toast({
        description: getUnknownErrorMessage(error, "Failed to update setting."),
        title: "Error",
        variant: "destructive",
      });
    }
  };

  const languages = [
    { code: "en", name: "English" },
    { code: "es", name: "Español" },
    { code: "fr", name: "Français" },
    { code: "de", name: "Deutsch" },
    { code: "it", name: "Italiano" },
    { code: "pt", name: "Português" },
    { code: "ja", name: "日本語" },
    { code: "ko", name: "한국어" },
    { code: "zh", name: "中文" },
  ];

  const currencies = [
    { code: "USD", name: "US Dollar", symbol: "$" },
    { code: "EUR", name: "Euro", symbol: "€" },
    { code: "GBP", name: "British Pound", symbol: "£" },
    { code: "JPY", name: "Japanese Yen", symbol: "¥" },
    { code: "CAD", name: "Canadian Dollar", symbol: "C$" },
    { code: "AUD", name: "Australian Dollar", symbol: "A$" },
    { code: "CHF", name: "Swiss Franc", symbol: "CHF" },
    { code: "CNY", name: "Chinese Yuan", symbol: "¥" },
  ];

  const timezones = [
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Asia/Kolkata",
    "Australia/Sydney",
  ];

  return (
    <div className="space-y-6">
      {/* Regional & Language Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GlobeIcon className="h-5 w-5" />
            Regional & Language
          </CardTitle>
          <CardDescription>
            Configure your language, currency, and regional preferences.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="language"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Language</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select language…" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {languages.map((lang) => (
                            <SelectItem key={lang.code} value={lang.code}>
                              {lang.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="currency"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Currency</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select currency…" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {currencies.map((curr) => (
                            <SelectItem key={curr.code} value={curr.code}>
                              {curr.symbol} {curr.name} ({curr.code})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="timezone"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Timezone</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select timezone…" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {timezones.map((tz) => (
                          <SelectItem key={tz} value={tz}>
                            {tz.replace(/_/g, " ")}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="units"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Units</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select units…" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="metric">Metric (km, °C)</SelectItem>
                          <SelectItem value="imperial">Imperial (mi, °F)</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="theme"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Theme</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select theme…" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="light">Light</SelectItem>
                          <SelectItem value="dark">Dark</SelectItem>
                          <SelectItem value="system">System</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="dateFormat"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Date Format</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select date format…" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="MM/DD/YYYY">MM/DD/YYYY</SelectItem>
                          <SelectItem value="DD/MM/YYYY">DD/MM/YYYY</SelectItem>
                          <SelectItem value="YYYY-MM-DD">YYYY-MM-DD</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="timeFormat"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Time Format</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select time format…" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="12h">12-hour (2:30 PM)</SelectItem>
                          <SelectItem value="24h">24-hour (14:30)</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="flex justify-end">
                <Button type="submit" disabled={form.formState.isSubmitting}>
                  {form.formState.isSubmitting ? "Saving…" : "Save Preferences"}
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>

      {/* Additional Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ZapIcon className="h-5 w-5" />
            Additional Settings
          </CardTitle>
          <CardDescription>
            Configure advanced features and experimental options.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {ADDITIONAL_SETTING_OPTIONS.map(
            ({ description, descriptionId, key, label, labelId }) => {
              const switchId = `${key}-switch`;

              return (
                <div className="flex items-center justify-between gap-4" key={key}>
                  <div className="flex flex-1 flex-col gap-0.5">
                    <Label
                      htmlFor={switchId}
                      className="cursor-pointer text-sm font-medium"
                      id={labelId}
                    >
                      {label}
                    </Label>
                    <p className="text-sm text-muted-foreground" id={descriptionId}>
                      {description}
                    </p>
                  </div>
                  <Switch
                    id={switchId}
                    aria-describedby={descriptionId}
                    checked={additionalSettings[key]}
                    onCheckedChange={(enabled) => toggleAdditionalSetting(key, enabled)}
                  />
                </div>
              );
            }
          )}
        </CardContent>
      </Card>
    </div>
  );
}
