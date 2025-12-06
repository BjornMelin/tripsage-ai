/**
 * @fileoverview Account settings section: email update, verification, and
 * notification preferences. UI only; server actions are stubbed.
 */

"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { type EmailUpdateFormData, emailUpdateFormSchema } from "@schemas/profile";
import { CheckIcon, MailIcon, Trash2Icon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
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
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/use-toast";
import { getBrowserClient } from "@/lib/supabase";
import { cn } from "@/lib/utils";
import { useAuthCore } from "@/stores/auth/auth-core";
import { useUserProfileStore } from "@/stores/user-store";

/**
 * Alert colors for account status indicators.
 * Deliberately distinct from statusVariants to keep lightweight, Tailwind-only tokens here.
 */
const ALERT_COLORS = {
  danger: {
    border: "border-red-200",
    buttonHover: "bg-red-600 hover:bg-red-700",
    title: "text-red-600",
  },
  warning: {
    bg: "bg-amber-50",
    border: "border-amber-200",
    text: "text-amber-700",
    title: "text-amber-800",
  },
} as const;

/**
 * Account settings panel component.
 *
 * @returns A settings section with email and notification controls.
 */
export function AccountSettingsSection() {
  const { profile, updatePersonalInfo: _updatePersonalInfo } = useUserProfileStore();
  const { user: authUser, setUser, logout } = useAuthCore();
  const { toast } = useToast();

  const currentEmail = authUser?.email ?? profile?.email ?? "";
  const [seenUnverified, setSeenUnverified] = useState(false);
  const isEmailVerified =
    seenUnverified || authUser?.isEmailVerified === false
      ? false
      : Boolean(authUser?.isEmailVerified ?? false);

  useEffect(() => {
    if (authUser?.isEmailVerified === false) {
      setSeenUnverified(true);
    }
  }, [authUser?.isEmailVerified]);

  const initialNotificationPrefs = useMemo(
    () => ({
      email: authUser?.preferences?.notifications?.email ?? true,
      marketing: authUser?.preferences?.notifications?.marketing ?? false,
      priceAlerts: authUser?.preferences?.notifications?.priceAlerts ?? true,
      tripReminders: authUser?.preferences?.notifications?.tripReminders ?? true,
    }),
    [authUser?.preferences?.notifications]
  );

  const [notificationPrefs, setNotificationPrefs] = useState(initialNotificationPrefs);
  const [isVerifyingEmail, setIsVerifyingEmail] = useState(false);
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);

  const emailForm = useForm<EmailUpdateFormData>({
    defaultValues: {
      email: currentEmail,
    },
    resolver: zodResolver(emailUpdateFormSchema),
  });

  useEffect(() => {
    emailForm.reset({ email: currentEmail });
  }, [currentEmail, emailForm]);

  useEffect(() => {
    setNotificationPrefs(initialNotificationPrefs);
  }, [initialNotificationPrefs]);

  const resolveSupabaseClient = () => {
    try {
      return getBrowserClient();
    } catch (_error) {
      return null;
    }
  };

  const onEmailUpdate = async (data: EmailUpdateFormData) => {
    try {
      const supabase = resolveSupabaseClient();
      if (!supabase) {
        throw new Error("Unable to access authentication client. Please try again.");
      }

      const { data: result, error } = await supabase.auth.updateUser({
        email: data.email,
      });

      if (error) {
        throw error;
      }

      const updatedEmail = result.user?.email ?? data.email;
      const verified = Boolean(result.user?.email_confirmed_at);

      if (authUser) {
        setUser({
          ...authUser,
          email: updatedEmail,
          isEmailVerified: verified,
          updatedAt: result.user?.updated_at ?? authUser.updatedAt,
        });
      }

      emailForm.reset({ email: updatedEmail });

      toast({
        description: verified
          ? "Your email has been updated."
          : "Please check your inbox to verify your new email address.",
        title: verified ? "Email updated" : "Verification required",
      });
    } catch (_error) {
      const description =
        _error instanceof Error
          ? _error.message
          : "Failed to update email. Please try again.";
      toast({
        description,
        title: "Error",
        variant: "destructive",
      });
    }
  };

  const handleEmailVerification = async () => {
    try {
      setIsVerifyingEmail(true);
      const response = await fetch("/auth/email/resend", {
        method: "POST",
      });

      if (!response.ok) {
        const errorData = (await response.json().catch(() => null)) as {
          message?: string;
        } | null;
        throw new Error(errorData?.message ?? "Failed to send verification email.");
      }

      toast({
        description: "Please check your inbox and click the verification link.",
        title: "Verification email sent",
      });
    } catch (_error) {
      const description =
        _error instanceof Error
          ? _error.message
          : "Failed to send verification email. Please try again.";
      toast({
        description,
        title: "Error",
        variant: "destructive",
      });
    } finally {
      setIsVerifyingEmail(false);
    }
  };

  const handleAccountDeletion = async () => {
    try {
      setIsDeletingAccount(true);
      const response = await fetch("/auth/delete", {
        method: "DELETE",
      });

      if (!response.ok) {
        const errorData = (await response.json().catch(() => null)) as {
          message?: string;
        } | null;
        throw new Error(errorData?.message ?? "Failed to delete account.");
      }

      await logout();

      toast({
        description: "Your account deletion request has been processed.",
        title: "Account deletion initiated",
      });
    } catch (_error) {
      const description =
        _error instanceof Error
          ? _error.message
          : "Failed to delete account. Please try again.";
      toast({
        description,
        title: "Error",
        variant: "destructive",
      });
    } finally {
      setIsDeletingAccount(false);
    }
  };

  const toggleNotificationSetting = async (
    setting: keyof typeof initialNotificationPrefs,
    enabled: boolean
  ) => {
    setNotificationPrefs((prev) => ({ ...prev, [setting]: enabled }));

    try {
      const supabase = resolveSupabaseClient();
      if (!supabase) {
        throw new Error("Unable to update notifications. Please try again.");
      }

      const nextNotifications = { ...notificationPrefs, [setting]: enabled };
      const nextPreferences = {
        ...(authUser?.preferences ?? {}),
        notifications: nextNotifications,
      };

      const { data, error } = await supabase.auth.updateUser({
        data: {
          preferences: nextPreferences,
        },
      });

      if (error) {
        throw error;
      }

      if (authUser) {
        setUser({
          ...authUser,
          preferences: nextPreferences,
          updatedAt: data.user?.updated_at ?? authUser.updatedAt,
        });
      }

      toast({
        description: `${setting} notifications ${enabled ? "enabled" : "disabled"}.`,
        title: "Settings updated",
      });
    } catch (_error) {
      setNotificationPrefs((prev) => ({ ...prev, [setting]: !enabled }));
      const description =
        _error instanceof Error
          ? _error.message
          : "Failed to update notification settings.";
      toast({
        description,
        title: "Error",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Email Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MailIcon className="h-5 w-5" />
            Email Settings
          </CardTitle>
          <CardDescription>
            Manage your email address and verification status.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Current Email:</span>
            <span className="text-sm">{currentEmail}</span>
            <Badge variant={isEmailVerified ? "default" : "secondary"}>
              {isEmailVerified ? (
                <>
                  <CheckIcon className="h-3 w-3 mr-1" />
                  Verified
                </>
              ) : (
                "Unverified"
              )}
            </Badge>
          </div>

          {!isEmailVerified && (
            <div
              className={cn(
                "rounded-lg border p-4",
                ALERT_COLORS.warning.border,
                ALERT_COLORS.warning.bg
              )}
            >
              <div className="flex justify-between items-center">
                <div>
                  <h4 className={cn("text-sm font-medium", ALERT_COLORS.warning.title)}>
                    Email verification required
                  </h4>
                  <p className={cn("text-sm", ALERT_COLORS.warning.text)}>
                    Please verify your email address to enable all features.
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleEmailVerification}
                  disabled={isVerifyingEmail}
                >
                  {isVerifyingEmail ? "Sending..." : "Send Verification"}
                </Button>
              </div>
            </div>
          )}

          <Form {...emailForm}>
            <form
              onSubmit={emailForm.handleSubmit(onEmailUpdate)}
              className="space-y-4"
            >
              <FormField
                control={emailForm.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Update Email Address</FormLabel>
                    <FormControl>
                      <Input placeholder="Enter new email address" {...field} />
                    </FormControl>
                    <FormDescription>
                      Changing your email will require verification of the new address.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit" disabled={emailForm.formState.isSubmitting}>
                {emailForm.formState.isSubmitting ? "Updating..." : "Update Email"}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>

      {/* Notification Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Notification Preferences</CardTitle>
          <CardDescription>
            Choose which notifications you'd like to receive.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <div className="text-sm font-medium">Email Notifications</div>
                <div className="text-sm text-muted-foreground">
                  Receive trip updates and important account information via email.
                </div>
              </div>
              <Switch
                checked={notificationPrefs.email}
                onCheckedChange={(enabled) =>
                  toggleNotificationSetting("email", enabled)
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <div className="text-sm font-medium">Trip Reminders</div>
                <div className="text-sm text-muted-foreground">
                  Get reminders about upcoming trips and bookings.
                </div>
              </div>
              <Switch
                checked={notificationPrefs.tripReminders}
                onCheckedChange={(enabled) =>
                  toggleNotificationSetting("tripReminders", enabled)
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <div className="text-sm font-medium">Price Alerts</div>
                <div className="text-sm text-muted-foreground">
                  Receive notifications when flight or hotel prices drop.
                </div>
              </div>
              <Switch
                checked={notificationPrefs.priceAlerts}
                onCheckedChange={(enabled) =>
                  toggleNotificationSetting("priceAlerts", enabled)
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <div className="text-sm font-medium">Marketing Communications</div>
                <div className="text-sm text-muted-foreground">
                  Receive promotional offers and travel tips.
                </div>
              </div>
              <Switch
                checked={notificationPrefs.marketing}
                onCheckedChange={(enabled) =>
                  toggleNotificationSetting("marketing", enabled)
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className={ALERT_COLORS.danger.border}>
        <CardHeader>
          <CardTitle className={ALERT_COLORS.danger.title}>Danger Zone</CardTitle>
          <CardDescription>
            Irreversible actions that will permanently affect your account.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" className="flex items-center gap-2">
                <Trash2Icon className="h-4 w-4" />
                Delete Account
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                <AlertDialogDescription>
                  This action cannot be undone. This will permanently delete your
                  account and remove all your data from our servers. All your trips,
                  bookings, and preferences will be lost.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  className={ALERT_COLORS.danger.buttonHover}
                  onClick={handleAccountDeletion}
                  disabled={isDeletingAccount}
                >
                  {isDeletingAccount ? "Deleting..." : "Yes, delete my account"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </CardContent>
      </Card>
    </div>
  );
}
