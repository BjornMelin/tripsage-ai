"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Check, Mail, Trash2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
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
import { useUserProfileStore } from "@/stores/user-store";

const emailUpdateSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
});

type EmailUpdateFormData = z.infer<typeof emailUpdateSchema>;

export function AccountSettingsSection() {
  const { profile, updatePersonalInfo: _updatePersonalInfo } = useUserProfileStore();
  const { toast } = useToast();

  const emailForm = useForm<EmailUpdateFormData>({
    resolver: zodResolver(emailUpdateSchema),
    defaultValues: {
      email: profile?.email || "",
    },
  });

  const onEmailUpdate = async (_data: EmailUpdateFormData) => {
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // Note: In a real app, this would update the auth email, not the profile
      toast({
        title: "Email updated",
        description: "Please check your inbox to verify your new email address.",
      });
    } catch (_error) {
      toast({
        title: "Error",
        description: "Failed to update email. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleEmailVerification = async () => {
    try {
      // Simulate sending verification email
      await new Promise((resolve) => setTimeout(resolve, 1000));

      toast({
        title: "Verification email sent",
        description: "Please check your inbox and click the verification link.",
      });
    } catch (_error) {
      toast({
        title: "Error",
        description: "Failed to send verification email. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleAccountDeletion = async () => {
    try {
      // Simulate account deletion
      await new Promise((resolve) => setTimeout(resolve, 1000));

      toast({
        title: "Account deletion initiated",
        description: "Your account deletion request has been processed.",
      });
    } catch (_error) {
      toast({
        title: "Error",
        description: "Failed to delete account. Please try again.",
        variant: "destructive",
      });
    }
  };

  const toggleNotificationSetting = async (setting: string, enabled: boolean) => {
    try {
      // Simulate API call to update notification settings
      await new Promise((resolve) => setTimeout(resolve, 500));

      // This would be updated when implementing real notification preferences
      toast({
        title: "Settings updated",
        description: `${setting} notifications ${enabled ? "enabled" : "disabled"}.`,
      });
    } catch (_error) {
      toast({
        title: "Error",
        description: "Failed to update notification settings.",
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
            <Mail className="h-5 w-5" />
            Email Settings
          </CardTitle>
          <CardDescription>
            Manage your email address and verification status.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Current Email:</span>
            <span className="text-sm">{profile?.email}</span>
            <Badge variant="default">
              <Check className="h-3 w-3 mr-1" />
              Verified
            </Badge>
          </div>

          {false && (
            <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
              <div className="flex justify-between items-center">
                <div>
                  <h4 className="text-sm font-medium text-yellow-800">
                    Email verification required
                  </h4>
                  <p className="text-sm text-yellow-700">
                    Please verify your email address to enable all features.
                  </p>
                </div>
                <Button size="sm" variant="outline" onClick={handleEmailVerification}>
                  Send Verification
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
                defaultChecked={true}
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
                defaultChecked={true}
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
                defaultChecked={true}
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
                defaultChecked={false}
                onCheckedChange={(enabled) =>
                  toggleNotificationSetting("marketing", enabled)
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-red-200">
        <CardHeader>
          <CardTitle className="text-red-600">Danger Zone</CardTitle>
          <CardDescription>
            Irreversible actions that will permanently affect your account.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" className="flex items-center gap-2">
                <Trash2 className="h-4 w-4" />
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
                  className="bg-red-600 hover:bg-red-700"
                  onClick={handleAccountDeletion}
                >
                  Yes, delete my account
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </CardContent>
      </Card>
    </div>
  );
}
