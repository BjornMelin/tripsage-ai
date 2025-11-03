/**
 * @fileoverview Security section: password change, 2FA toggle, active sessions
 * management, and basic recommendations. UI only; actions are stubbed.
 */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Clock, Eye, EyeOff, Key, Shield, Smartphone } from "lucide-react";
import { useState } from "react";
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

const PasswordChangeSchema = z
  .object({
    confirmPassword: z.string(),
    currentPassword: z.string().min(1, "Current password is required"),
    newPassword: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(
        /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
        "Password must contain at least one uppercase letter, one lowercase letter, and one number"
      ),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  });

type PasswordChangeFormData = z.infer<typeof PasswordChangeSchema>;

interface SecurityDevice {
  id: string;
  name: string;
  type: "mobile" | "desktop" | "tablet";
  lastUsed: string;
  location: string;
  current: boolean;
}

/**
 * Security settings panel component.
 * @returns A section for authentication and session management.
 */
export function SecuritySection() {
  const { profile: _profile } = useUserProfileStore();
  const { toast } = useToast();
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const passwordForm = useForm<PasswordChangeFormData>({
    defaultValues: {
      confirmPassword: "",
      currentPassword: "",
      newPassword: "",
    },
    resolver: zodResolver(PasswordChangeSchema),
  });

  // Mock security devices data
  const securityDevices: SecurityDevice[] = [
    {
      current: true,
      id: "1",
      lastUsed: "2 minutes ago",
      location: "New York, USA",
      name: "Chrome on Windows",
      type: "desktop",
    },
    {
      current: false,
      id: "2",
      lastUsed: "3 hours ago",
      location: "New York, USA",
      name: "Safari on iPhone",
      type: "mobile",
    },
    {
      current: false,
      id: "3",
      lastUsed: "2 days ago",
      location: "San Francisco, USA",
      name: "Firefox on MacBook",
      type: "desktop",
    },
  ];

  const onPasswordChange = async (_data: PasswordChangeFormData) => {
    try {
      // Simulate API call for password change
      await new Promise((resolve) => setTimeout(resolve, 1500));

      passwordForm.reset();
      toast({
        description: "Your password has been successfully changed.",
        title: "Password updated",
      });
    } catch (_error) {
      toast({
        description:
          "Failed to update password. Please check your current password and try again.",
        title: "Error",
        variant: "destructive",
      });
    }
  };

  // TODO: Integrate real 2FA API and persist state.
  const toggle2fa = async (enabled: boolean) => {
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // Note: This would be updated when implementing real 2FA settings
      toast({
        description: enabled
          ? "Two-factor authentication has been enabled for your account."
          : "Two-factor authentication has been disabled.",
        title: enabled ? "2FA enabled" : "2FA disabled",
      });
    } catch (_error) {
      toast({
        description: "Failed to update two-factor authentication settings.",
        title: "Error",
        variant: "destructive",
      });
    }
  };

  // TODO: Revoke device via API and invalidate session list.
  const revokeDevice = async (_deviceId: string) => {
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));

      toast({
        description: "The device has been successfully revoked from your account.",
        title: "Device revoked",
      });
    } catch (_error) {
      toast({
        description: "Failed to revoke device access.",
        title: "Error",
        variant: "destructive",
      });
    }
  };

  const getDeviceIcon = (type: string) => {
    switch (type) {
      case "mobile":
        return <Smartphone className="h-4 w-4" />;
      case "tablet":
        return <Smartphone className="h-4 w-4" />;
      default:
        return <Shield className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Password Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            Password & Authentication
          </CardTitle>
          <CardDescription>
            Update your password and manage authentication settings.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <Form {...passwordForm}>
            <form
              onSubmit={passwordForm.handleSubmit(onPasswordChange)}
              className="space-y-4"
            >
              <FormField
                control={passwordForm.control}
                name="currentPassword"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Current Password</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          type={showCurrentPassword ? "text" : "password"}
                          placeholder="Enter your current password"
                          {...field}
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                          onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                        >
                          {showCurrentPassword ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </Button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={passwordForm.control}
                name="newPassword"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>New Password</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          type={showNewPassword ? "text" : "password"}
                          placeholder="Enter your new password"
                          {...field}
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                          onClick={() => setShowNewPassword(!showNewPassword)}
                        >
                          {showNewPassword ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </Button>
                      </div>
                    </FormControl>
                    <FormDescription>
                      Password must be at least 8 characters with uppercase, lowercase,
                      and numbers.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={passwordForm.control}
                name="confirmPassword"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Confirm New Password</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          type={showConfirmPassword ? "text" : "password"}
                          placeholder="Confirm your new password"
                          {...field}
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        >
                          {showConfirmPassword ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </Button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Button type="submit" disabled={passwordForm.formState.isSubmitting}>
                {passwordForm.formState.isSubmitting
                  ? "Updating..."
                  : "Update Password"}
              </Button>
            </form>
          </Form>

          {/* Two-Factor Authentication */}
          <div className="pt-6 border-t">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-medium">Two-Factor Authentication</h3>
                  <Badge variant="secondary">Disabled</Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  Add an extra layer of security to your account with 2FA.
                </p>
              </div>
              <Switch checked={false} onCheckedChange={toggle2fa} />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Active Sessions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Active Sessions
          </CardTitle>
          <CardDescription>
            Manage devices and browsers that are currently signed in to your account.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {securityDevices.map((device) => (
              <div
                key={device.id}
                className="flex items-center justify-between p-4 border rounded-lg"
              >
                <div className="flex items-center gap-3">
                  {getDeviceIcon(device.type)}
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{device.name}</span>
                      {device.current && (
                        <Badge variant="outline" className="text-xs">
                          Current
                        </Badge>
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {device.location} • Last used {device.lastUsed}
                    </div>
                  </div>
                </div>
                {!device.current && (
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button variant="ghost" size="sm">
                        Revoke
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Revoke device access?</AlertDialogTitle>
                        <AlertDialogDescription>
                          This will sign out {device.name} from your account. You'll
                          need to sign in again to use this device.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={() => revokeDevice(device.id)}>
                          Revoke Access
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Security Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle>Security Recommendations</CardTitle>
          <CardDescription>Tips to keep your account secure.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
              <Shield className="h-5 w-5 text-blue-600 mt-0.5" />
              <div className="space-y-1">
                <h4 className="text-sm font-medium text-blue-900">
                  Enable Two-Factor Authentication
                </h4>
                <p className="text-sm text-blue-700">
                  Add an extra layer of security by enabling 2FA for your account.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
              <Key className="h-5 w-5 text-green-600 mt-0.5" />
              <div className="space-y-1">
                <h4 className="text-sm font-medium text-green-900">
                  Use a Strong Password
                </h4>
                <p className="text-sm text-green-700">
                  Your password should be at least 12 characters long and include a mix
                  of letters, numbers, and symbols.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
              <Clock className="h-5 w-5 text-yellow-600 mt-0.5" />
              <div className="space-y-1">
                <h4 className="text-sm font-medium text-yellow-900">
                  Review Active Sessions
                </h4>
                <p className="text-sm text-yellow-700">
                  Regularly check and revoke access for devices you no longer use.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
