/**
 * @fileoverview Personal info section: update profile picture and personal details.
 */

"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { type PersonalInfoFormData, personalInfoFormSchema } from "@schemas/profile";
import { CameraIcon, UploadIcon } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
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
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";
import { getUnknownErrorMessage } from "@/lib/errors/get-unknown-error-message";
import { getBrowserClient } from "@/lib/supabase";
import { useAuthCore } from "@/stores/auth/auth-core";

const MAX_AVATAR_BYTES = 5 * 1024 * 1024;
const SUPPORTED_AVATAR_TYPES = {
  "image/avif": "avif",
  "image/gif": "gif",
  "image/jpeg": "jpg",
  "image/jpg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
} as const;
type SupportedAvatarType = keyof typeof SUPPORTED_AVATAR_TYPES;
type SupportedAvatarExt = (typeof SUPPORTED_AVATAR_TYPES)[SupportedAvatarType];

function resolveAvatarExt(file: File): SupportedAvatarExt | null {
  return (
    (SUPPORTED_AVATAR_TYPES as Record<string, SupportedAvatarExt>)[file.type] ?? null
  );
}

export function PersonalInfoSection() {
  const avatarInputId = useId();
  const avatarInputRef = useRef<HTMLInputElement | null>(null);
  const { user: authUser, setUser } = useAuthCore();
  const { toast } = useToast();
  const [isUploading, setIsUploading] = useState(false);

  const defaultValues = useMemo(
    (): PersonalInfoFormData => ({
      bio: authUser?.bio ?? "",
      displayName:
        authUser?.displayName ?? (authUser?.email ? authUser.email.split("@")[0] : ""),
      firstName: authUser?.firstName ?? "",
      lastName: authUser?.lastName ?? "",
      location: authUser?.location ?? "",
      website: authUser?.website ?? "",
    }),
    [authUser]
  );

  const form = useForm<PersonalInfoFormData>({
    defaultValues,
    resolver: zodResolver(personalInfoFormSchema as never),
  });

  useEffect(() => {
    form.reset(defaultValues);
  }, [defaultValues, form]);

  const resolveSupabaseClient = () => {
    try {
      return getBrowserClient();
    } catch (_error) {
      return null;
    }
  };

  const onSubmit = async (data: PersonalInfoFormData) => {
    try {
      if (!authUser) {
        throw new Error("You must be signed in to update your profile.");
      }

      const supabase = resolveSupabaseClient();
      if (!supabase) {
        throw new Error("Unable to access profile client. Please try again.");
      }

      const bio = data.bio?.trim() ? data.bio.trim() : undefined;
      const location = data.location?.trim() ? data.location.trim() : undefined;
      const website = data.website?.trim() ? data.website.trim() : undefined;

      const { data: result, error } = await supabase.auth.updateUser({
        data: {
          bio: bio ?? null,
          display_name: data.displayName,
          first_name: data.firstName,
          full_name: data.displayName,
          last_name: data.lastName,
          location: location ?? null,
          website: website ?? null,
        },
      });

      if (error) {
        throw error;
      }

      setUser({
        ...authUser,
        bio,
        displayName: data.displayName,
        firstName: data.firstName,
        lastName: data.lastName,
        location,
        updatedAt: result.user?.updated_at ?? authUser.updatedAt,
        website,
      });

      toast({
        description: "Your personal information has been successfully updated.",
        title: "Profile updated",
      });
    } catch (error) {
      toast({
        description: getUnknownErrorMessage(
          error,
          "Failed to update profile. Please try again."
        ),
        title: "Error",
        variant: "destructive",
      });
    }
  };

  const handleAvatarUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const ext = resolveAvatarExt(file);
    if (!ext) {
      toast({
        description:
          "Please select a supported image file (jpg, png, gif, webp, avif).",
        title: "Invalid file type",
        variant: "destructive",
      });
      return;
    }

    if (file.size > MAX_AVATAR_BYTES) {
      toast({
        description: "Please select an image smaller than 5MB.",
        title: "File too large",
        variant: "destructive",
      });
      return;
    }

    setIsUploading(true);
    try {
      if (!authUser) {
        throw new Error("You must be signed in to update your avatar.");
      }

      const supabase = resolveSupabaseClient();
      if (!supabase) {
        throw new Error("Unable to access profile client. Please try again.");
      }

      const avatarPath = `${authUser.id}.${ext}`;
      const otherPaths = (Object.values(SUPPORTED_AVATAR_TYPES) as SupportedAvatarExt[])
        .filter((candidate) => candidate !== ext)
        .map((candidate) => `${authUser.id}.${candidate}`);

      if (otherPaths.length > 0) {
        await supabase.storage.from("avatars").remove(otherPaths);
      }

      const { error: uploadError } = await supabase.storage
        .from("avatars")
        .upload(avatarPath, file, {
          cacheControl: "0",
          contentType: file.type,
          upsert: true,
        });

      if (uploadError) {
        throw uploadError;
      }

      const { data } = supabase.storage.from("avatars").getPublicUrl(avatarPath);
      const avatarUrl = data.publicUrl;

      const { data: updateResult, error: updateError } = await supabase.auth.updateUser(
        {
          data: {
            avatar_url: avatarUrl,
          },
        }
      );

      if (updateError) {
        throw updateError;
      }

      setUser({
        ...authUser,
        avatarUrl,
        updatedAt: updateResult.user?.updated_at ?? authUser.updatedAt,
      });

      toast({
        description: "Your profile picture has been successfully updated.",
        title: "Avatar updated",
      });
    } catch (error) {
      toast({
        description: getUnknownErrorMessage(
          error,
          "Failed to upload avatar. Please try again."
        ),
        title: "Upload failed",
        variant: "destructive",
      });
    } finally {
      event.target.value = "";
      setIsUploading(false);
    }
  };

  const getInitials = (firstName?: string, lastName?: string, displayName?: string) => {
    if (firstName && lastName) {
      return `${firstName[0]}${lastName[0]}`.toUpperCase();
    }
    if (displayName) {
      const parts = displayName.split(" ");
      return parts.length > 1
        ? `${parts[0][0]}${parts[1][0]}`.toUpperCase()
        : displayName.slice(0, 2).toUpperCase();
    }
    return authUser?.email?.slice(0, 2).toUpperCase() || "U";
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Personal Information</CardTitle>
        <CardDescription>
          Update your personal details and profile picture.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Avatar Upload Section */}
        <div className="flex items-center gap-6">
          <div className="relative">
            <Avatar className="h-24 w-24">
              <AvatarImage
                src={authUser?.avatarUrl}
                alt={
                  authUser?.displayName
                    ? `${authUser.displayName} profile picture`
                    : "Profile picture"
                }
              />
              <AvatarFallback className="text-lg">
                {getInitials(
                  authUser?.firstName,
                  authUser?.lastName,
                  authUser?.displayName
                )}
              </AvatarFallback>
            </Avatar>
            <div className="absolute -bottom-2 -right-2">
              <Button
                size="sm"
                variant="outline"
                className="h-8 w-8 rounded-full p-0"
                onClick={() => avatarInputRef.current?.click()}
                disabled={isUploading}
              >
                {isUploading ? (
                  <UploadIcon className="h-3 w-3 animate-spin" />
                ) : (
                  <CameraIcon className="h-3 w-3" />
                )}
              </Button>
            </div>
            <input
              id={avatarInputId}
              ref={avatarInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleAvatarUpload}
            />
          </div>
          <div className="space-y-1">
            <h3 className="font-medium">Profile Picture</h3>
            <p className="text-sm text-muted-foreground">
              Click the camera icon to upload a new profile picture. Recommended size:
              400x400px. Max file size: 5MB.
            </p>
          </div>
        </div>

        {/* Personal Information Form */}
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="firstName"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>First Name</FormLabel>
                    <FormControl>
                      <Input placeholder="Enter your first name" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="lastName"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Last Name</FormLabel>
                    <FormControl>
                      <Input placeholder="Enter your last name" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="displayName"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Display Name</FormLabel>
                  <FormControl>
                    <Input placeholder="Enter your display name" {...field} />
                  </FormControl>
                  <FormDescription>
                    This is the name that will be displayed to other users.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="bio"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Bio</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Tell us a little about yourself"
                      className="min-h-[100px]"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Share a brief description about yourself (optional).
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="location"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Location</FormLabel>
                    <FormControl>
                      <Input placeholder="City, Country" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="website"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Website</FormLabel>
                    <FormControl>
                      <Input placeholder="https://example.com" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="flex justify-end">
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
