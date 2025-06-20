"use client";

import { SecurityDashboard } from "@/components/features/security/security-dashboard";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { useAuth } from "@/contexts/auth-context";
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  Download,
  Eye,
  Key,
  Lock,
  Shield,
  Smartphone,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

interface SecuritySettings {
  twoFactorEnabled: boolean;
  emailNotifications: boolean;
  securityAlerts: boolean;
  loginNotifications: boolean;
  deviceTracking: boolean;
  dataEncryption: boolean;
}

export default function SecuritySettingsPage() {
  const { user } = useAuth();
  const [settings, setSettings] = useState<SecuritySettings>({
    twoFactorEnabled: false,
    emailNotifications: true,
    securityAlerts: true,
    loginNotifications: true,
    deviceTracking: true,
    dataEncryption: true,
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleSettingChange = async (key: keyof SecuritySettings, value: boolean) => {
    setIsLoading(true);
    try {
      // TODO: Implement API call to update settings
      setSettings((prev) => ({ ...prev, [key]: value }));

      // Simulate API delay
      await new Promise((resolve) => setTimeout(resolve, 500));
    } catch (error) {
      console.error("Failed to update setting:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownloadSecurityData = async () => {
    try {
      // TODO: Implement security data export
      console.log("Downloading security data...");
    } catch (error) {
      console.error("Failed to download security data:", error);
    }
  };

  const handleDeleteAccount = async () => {
    try {
      // TODO: Implement account deletion
      console.log("Account deletion requested...");
    } catch (error) {
      console.error("Failed to delete account:", error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Security Settings</h1>
          <p className="text-muted-foreground">
            Manage your account security and privacy preferences
          </p>
        </div>
        <Badge variant="outline" className="flex items-center">
          <Shield className="mr-1 h-3 w-3" />
          Secure Account
        </Badge>
      </div>

      {/* Security Dashboard */}
      <SecurityDashboard />

      <Separator />

      {/* Security Settings */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Authentication Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Lock className="mr-2 h-5 w-5" />
              Authentication
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Two-Factor Authentication */}
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label className="text-base font-medium">
                  Two-Factor Authentication
                </Label>
                <p className="text-sm text-muted-foreground">
                  Add an extra layer of security to your account
                </p>
              </div>
              <div className="flex items-center space-x-2">
                {settings.twoFactorEnabled && (
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                )}
                <Switch
                  checked={settings.twoFactorEnabled}
                  onCheckedChange={(checked) =>
                    handleSettingChange("twoFactorEnabled", checked)
                  }
                  disabled={isLoading}
                />
              </div>
            </div>

            {!settings.twoFactorEnabled && (
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  Enable two-factor authentication for enhanced security.
                  <Button variant="link" className="h-auto p-0 ml-2">
                    Set up now
                  </Button>
                </AlertDescription>
              </Alert>
            )}

            <Separator />

            {/* Password */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-base font-medium">Password</Label>
                  <p className="text-sm text-muted-foreground">
                    Last changed 30 days ago
                  </p>
                </div>
                <Button variant="outline" size="sm" asChild>
                  <Link href="/auth/reset-password">Change Password</Link>
                </Button>
              </div>
            </div>

            <Separator />

            {/* API Keys */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-base font-medium">API Keys</Label>
                  <p className="text-sm text-muted-foreground">
                    Manage your service API keys
                  </p>
                </div>
                <Button variant="outline" size="sm" asChild>
                  <Link href="/settings/api-keys">
                    <Key className="mr-2 h-4 w-4" />
                    Manage Keys
                  </Link>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Notification Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Bell className="mr-2 h-5 w-5" />
              Security Notifications
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Email Notifications */}
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label className="text-base font-medium">Email Notifications</Label>
                <p className="text-sm text-muted-foreground">
                  Receive security alerts via email
                </p>
              </div>
              <Switch
                checked={settings.emailNotifications}
                onCheckedChange={(checked) =>
                  handleSettingChange("emailNotifications", checked)
                }
                disabled={isLoading}
              />
            </div>

            <Separator />

            {/* Security Alerts */}
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label className="text-base font-medium">Security Alerts</Label>
                <p className="text-sm text-muted-foreground">
                  Get notified of suspicious activity
                </p>
              </div>
              <Switch
                checked={settings.securityAlerts}
                onCheckedChange={(checked) =>
                  handleSettingChange("securityAlerts", checked)
                }
                disabled={isLoading}
              />
            </div>

            <Separator />

            {/* Login Notifications */}
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label className="text-base font-medium">Login Notifications</Label>
                <p className="text-sm text-muted-foreground">
                  Get notified of new sign-ins
                </p>
              </div>
              <Switch
                checked={settings.loginNotifications}
                onCheckedChange={(checked) =>
                  handleSettingChange("loginNotifications", checked)
                }
                disabled={isLoading}
              />
            </div>
          </CardContent>
        </Card>

        {/* Privacy Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Eye className="mr-2 h-5 w-5" />
              Privacy & Data
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Device Tracking */}
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label className="text-base font-medium">Device Tracking</Label>
                <p className="text-sm text-muted-foreground">
                  Track devices for security monitoring
                </p>
              </div>
              <Switch
                checked={settings.deviceTracking}
                onCheckedChange={(checked) =>
                  handleSettingChange("deviceTracking", checked)
                }
                disabled={isLoading}
              />
            </div>

            <Separator />

            {/* Data Encryption */}
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label className="text-base font-medium">Data Encryption</Label>
                <p className="text-sm text-muted-foreground">
                  Encrypt sensitive data at rest
                </p>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <Badge variant="secondary">Always On</Badge>
              </div>
            </div>

            <Separator />

            {/* Data Export */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-base font-medium">Data Export</Label>
                  <p className="text-sm text-muted-foreground">
                    Download your security data
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDownloadSecurityData}
                >
                  <Download className="mr-2 h-4 w-4" />
                  Export Data
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Connected Accounts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Smartphone className="mr-2 h-5 w-5" />
              Connected Accounts
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Google Account */}
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-red-100 rounded flex items-center justify-center">
                  <span className="text-sm font-bold text-red-600">G</span>
                </div>
                <div>
                  <p className="font-medium">Google</p>
                  <p className="text-sm text-muted-foreground">Connected</p>
                </div>
              </div>
              <Button variant="ghost" size="sm">
                Disconnect
              </Button>
            </div>

            {/* GitHub Account */}
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-gray-100 rounded flex items-center justify-center">
                  <span className="text-sm font-bold text-gray-600">GH</span>
                </div>
                <div>
                  <p className="font-medium">GitHub</p>
                  <p className="text-sm text-muted-foreground">Not connected</p>
                </div>
              </div>
              <Button variant="outline" size="sm">
                Connect
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <Separator />

      {/* Danger Zone */}
      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="flex items-center text-destructive">
            <AlertTriangle className="mr-2 h-5 w-5" />
            Danger Zone
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              These actions are irreversible. Please proceed with caution.
            </AlertDescription>
          </Alert>

          <div className="flex items-center justify-between">
            <div>
              <Label className="text-base font-medium">Delete Account</Label>
              <p className="text-sm text-muted-foreground">
                Permanently delete your account and all associated data
              </p>
            </div>
            <Button variant="destructive" size="sm" onClick={handleDeleteAccount}>
              <Trash2 className="mr-2 h-4 w-4" />
              Delete Account
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
