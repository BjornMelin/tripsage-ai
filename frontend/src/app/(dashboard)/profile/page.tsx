"use client";

import { Settings, Shield, Sliders, User } from "lucide-react";
import Link from "next/link";
import { AccountSettingsSection } from "@/components/features/profile/account-settings-section";
import { PersonalInfoSection } from "@/components/features/profile/personal-info-section";
import { PreferencesSection } from "@/components/features/profile/preferences-section";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuthCore } from "@/stores/auth/auth-core";
import { useUserProfileStore } from "@/stores/user-store";

export default function ProfilePage() {
  const { user, isLoading } = useAuthCore();
  const { profile: _profile, isLoading: isProfileLoading } = useUserProfileStore();

  if (isLoading || isProfileLoading) {
    return (
      <div className="container mx-auto py-6 space-y-8">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-96" />
        </div>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-64" />
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="container mx-auto py-6">
        <Card>
          <CardHeader>
            <CardTitle>Profile Not Found</CardTitle>
            <CardDescription>Please log in to view your profile.</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-8">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Profile</h1>
        <p className="text-muted-foreground">
          Manage your account settings and preferences.
        </p>
      </div>

      <Tabs defaultValue="personal" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="personal" className="flex items-center gap-2">
            <User className="h-4 w-4" />
            Personal
          </TabsTrigger>
          <TabsTrigger value="account" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Account
          </TabsTrigger>
          <TabsTrigger value="preferences" className="flex items-center gap-2">
            <Sliders className="h-4 w-4" />
            Preferences
          </TabsTrigger>
        </TabsList>

        <TabsContent value="personal" className="space-y-6">
          <PersonalInfoSection />
        </TabsContent>

        <TabsContent value="account" className="space-y-6">
          <AccountSettingsSection />
        </TabsContent>

        <TabsContent value="preferences" className="space-y-6">
          <PreferencesSection />
        </TabsContent>
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Security & MFA
          </CardTitle>
          <CardDescription>
            Manage multi-factor authentication and backup codes in the security console.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link href="/security">Open Security Console</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
