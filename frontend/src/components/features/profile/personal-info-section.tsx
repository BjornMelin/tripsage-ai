/**
 * @fileoverview Personal info section: update profile picture and personal details.
 * UI only; server actions are stubbed.
 */

"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { type PersonalInfoFormData, personalInfoFormSchema } from "@schemas/profile";
import { CameraIcon, UploadIcon } from "lucide-react";
import { useId, useState } from "react";
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
import { useUserProfileStore } from "@/stores/user-store";

export function PersonalInfoSection() {
  const avatarInputId = useId();
  const { profile, updatePersonalInfo, uploadAvatar } = useUserProfileStore();
  const { toast } = useToast();
  const [isUploading, setIsUploading] = useState(false);

  const form = useForm<PersonalInfoFormData>({
    defaultValues: {
      bio: profile?.personalInfo?.bio || "",
      displayName: profile?.personalInfo?.displayName || "",
      firstName: profile?.personalInfo?.firstName || "",
      lastName: profile?.personalInfo?.lastName || "",
      location: profile?.personalInfo?.location || "",
      website: profile?.personalInfo?.website || "",
    },
    resolver: zodResolver(personalInfoFormSchema),
  });

  const onSubmit = async (data: PersonalInfoFormData) => {
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));

      await updatePersonalInfo(data);
      toast({
        description: "Your personal information has been successfully updated.",
        title: "Profile updated",
      });
    } catch (_error) {
      toast({
        description: "Failed to update profile. Please try again.",
        title: "Error",
        variant: "destructive",
      });
    }
  };

  const handleAvatarUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith("image/")) {
      toast({
        description: "Please select an image file.",
        title: "Invalid file type",
        variant: "destructive",
      });
      return;
    }

    // Validate file size (5MB limit)
    if (file.size > 5 * 1024 * 1024) {
      toast({
        description: "Please select an image smaller than 5MB.",
        title: "File too large",
        variant: "destructive",
      });
      return;
    }

    setIsUploading(true);
    try {
      const avatarUrl = await uploadAvatar(file);

      if (avatarUrl) {
        toast({
          description: "Your profile picture has been successfully updated.",
          title: "Avatar updated",
        });
      } else {
        throw new Error("Upload failed");
      }
    } catch (_error) {
      toast({
        description: "Failed to upload avatar. Please try again.",
        title: "Upload failed",
        variant: "destructive",
      });
    } finally {
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
    return profile?.email?.slice(0, 2).toUpperCase() || "U";
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
              <AvatarImage src={profile?.avatarUrl} alt="Profile picture" />
              <AvatarFallback className="text-lg">
                {getInitials(
                  profile?.personalInfo?.firstName,
                  profile?.personalInfo?.lastName,
                  profile?.personalInfo?.displayName
                )}
              </AvatarFallback>
            </Avatar>
            <div className="absolute -bottom-2 -right-2">
              <Button
                size="sm"
                variant="outline"
                className="h-8 w-8 rounded-full p-0"
                onClick={() => document.getElementById(avatarInputId)?.click()}
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
