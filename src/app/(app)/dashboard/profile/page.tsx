/**
 * @fileoverview The profile page for the dashboard.
 */

"use client";

import { SettingsIcon, ShieldIcon, SlidersIcon, UserIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
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
import { useAuthCore } from "@/features/auth/store/auth/auth-core";
import { AccountSettingsSection } from "@/features/profile/components/account-settings-section";
import { PersonalInfoSection } from "@/features/profile/components/personal-info-section";
import { PreferencesSection } from "@/features/profile/components/preferences-section";
import { ROUTES } from "@/lib/routes";

export default function ProfilePage() {
  const router = useRouter();
  const hasInitialized = useAuthCore((state) => state.hasInitialized);
  const initialize = useAuthCore((state) => state.initialize);
  const isLoading = useAuthCore((state) => state.isLoading);
  const user = useAuthCore((state) => state.user);

  useEffect(() => {
    if (hasInitialized || isLoading) return;
    initialize().catch(() => undefined);
  }, [hasInitialized, initialize, isLoading]);

  useEffect(() => {
    if (!hasInitialized || isLoading) return;
    if (user) return;
    const query = new URLSearchParams({ from: ROUTES.dashboard.profile }).toString();
    const target = `${ROUTES.login}?${query}`;
    router.replace(target);
  }, [hasInitialized, isLoading, router, user]);

  if ((!hasInitialized || isLoading) && !user) {
    return (
      <div
        className="container mx-auto py-6 space-y-8"
        aria-busy="true"
        aria-live="polite"
      >
        <output className="sr-only" aria-label="Loading content">
          Loading…
        </output>
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" aria-hidden="true" />
          <Skeleton className="h-4 w-96" aria-hidden="true" />
        </div>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-32" aria-hidden="true" />
            <Skeleton className="h-4 w-64" aria-hidden="true" />
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Skeleton className="h-10 w-full" aria-hidden="true" />
              <Skeleton className="h-10 w-full" aria-hidden="true" />
              <Skeleton className="h-10 w-full" aria-hidden="true" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!user) {
    return null;
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
            <UserIcon className="h-4 w-4" />
            Personal
          </TabsTrigger>
          <TabsTrigger value="account" className="flex items-center gap-2">
            <SettingsIcon className="h-4 w-4" />
            Account
          </TabsTrigger>
          <TabsTrigger value="preferences" className="flex items-center gap-2">
            <SlidersIcon className="h-4 w-4" />
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
            <ShieldIcon className="h-4 w-4" />
            Security & MFA
          </CardTitle>
          <CardDescription>
            Manage multi-factor authentication and backup codes in the security console.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link href={ROUTES.dashboard.security}>Open Security Console</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
