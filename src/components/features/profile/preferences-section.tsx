/**
 * @fileoverview Preferences section: update currency, language, timezone, and units.
 */

"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { CURRENCY_CODE_SCHEMA, type CurrencyCode } from "@schemas/currency";
import { type PreferencesFormData, preferencesFormSchema } from "@schemas/profile";
import { GlobeIcon, ZapIcon } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/use-toast";
import { getUnknownErrorMessage } from "@/lib/errors/get-unknown-error-message";
import { getBrowserClient } from "@/lib/supabase";
import { useAuthCore } from "@/stores/auth/auth-core";
import { useCurrencyStore } from "@/stores/currency-store";

type AdditionalSettingKey =
  | "analytics"
  | "autoSaveSearches"
  | "locationServices"
  | "smartSuggestions";

export function PreferencesSection() {
  const { user: authUser, setUser } = useAuthCore();
  const { baseCurrency, setBaseCurrency } = useCurrencyStore();
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

  const form = useForm<PreferencesFormData>({
    defaultValues,
    resolver: zodResolver(preferencesFormSchema),
  });

  useEffect(() => {
    form.reset(defaultValues);
  }, [defaultValues, form]);

  useEffect(() => {
    setAdditionalSettings(initialAdditionalSettings);
  }, [initialAdditionalSettings]);

  const resolveSupabaseClient = () => {
    try {
      return getBrowserClient();
    } catch (_error) {
      return null;
    }
  };

  const onSubmit = async (data: PreferencesFormData) => {
    try {
      if (!authUser) {
        throw new Error("You must be signed in to update your preferences.");
      }

      const supabase = resolveSupabaseClient();
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
        const currency = CURRENCY_CODE_SCHEMA.parse(data.currency) as CurrencyCode;
        setBaseCurrency(currency);
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
    setAdditionalSettings((prev) => ({ ...prev, [setting]: enabled }));

    try {
      if (!authUser) {
        throw new Error("You must be signed in to update your preferences.");
      }

      const supabase = resolveSupabaseClient();
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
        description: `${setting} ${enabled ? "enabled" : "disabled"}.`,
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
                            <SelectValue placeholder="Select language" />
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
                            <SelectValue placeholder="Select currency" />
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
                          <SelectValue placeholder="Select timezone" />
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
                            <SelectValue placeholder="Select units" />
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
                            <SelectValue placeholder="Select theme" />
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
                            <SelectValue placeholder="Select date format" />
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
                            <SelectValue placeholder="Select time format" />
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
                  {form.formState.isSubmitting ? "Saving..." : "Save Preferences"}
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
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-sm font-medium">Auto-save Searches</div>
              <div className="text-sm text-muted-foreground">
                Automatically save your search history for quick access.
              </div>
            </div>
            <Switch
              checked={additionalSettings.autoSaveSearches}
              onCheckedChange={(enabled) =>
                toggleAdditionalSetting("autoSaveSearches", enabled)
              }
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-sm font-medium">Smart Suggestions</div>
              <div className="text-sm text-muted-foreground">
                Get AI-powered travel suggestions based on your preferences.
              </div>
            </div>
            <Switch
              checked={additionalSettings.smartSuggestions}
              onCheckedChange={(enabled) =>
                toggleAdditionalSetting("smartSuggestions", enabled)
              }
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-sm font-medium">Location Services</div>
              <div className="text-sm text-muted-foreground">
                Allow location access for nearby recommendations.
              </div>
            </div>
            <Switch
              checked={additionalSettings.locationServices}
              onCheckedChange={(enabled) =>
                toggleAdditionalSetting("locationServices", enabled)
              }
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-sm font-medium">Analytics</div>
              <div className="text-sm text-muted-foreground">
                Help us improve by sharing anonymous usage data.
              </div>
            </div>
            <Switch
              checked={additionalSettings.analytics}
              onCheckedChange={(enabled) =>
                toggleAdditionalSetting("analytics", enabled)
              }
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
