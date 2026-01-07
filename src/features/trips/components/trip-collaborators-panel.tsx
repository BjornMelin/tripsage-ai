/**
 * @fileoverview Trip collaborators management panel.
 */

"use client";

import {
  type TripCollaborator,
  type TripCollaboratorRole,
  tripCollaboratorInviteSchema,
  tripCollaboratorRoleSchema,
} from "@schemas/trips";
import {
  CrownIcon,
  LinkIcon,
  Loader2Icon,
  ShieldIcon,
  Trash2Icon,
  UserPlusIcon,
} from "lucide-react";
import { useState } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/components/ui/use-toast";
import {
  useInviteTripCollaborator,
  useRemoveTripCollaborator,
  useUpdateTripCollaboratorRole,
} from "@/hooks/use-trip-collaborators";
import { useZodForm } from "@/hooks/use-zod-form";
import { copyToClipboardWithToast } from "@/lib/client/clipboard";
import { cn } from "@/lib/utils";

const ROLE_META: Record<
  TripCollaboratorRole,
  { icon: typeof ShieldIcon; label: string; badge: string }
> = {
  editor: {
    badge: "bg-sky-500/10 text-sky-700 dark:text-sky-300",
    icon: ShieldIcon,
    label: "Editor",
  },
  owner: {
    badge: "bg-amber-500/10 text-amber-700 dark:text-amber-300",
    icon: CrownIcon,
    label: "Owner",
  },
  viewer: {
    badge: "bg-muted text-muted-foreground",
    icon: ShieldIcon,
    label: "Viewer",
  },
};

function GetInitialsFromEmail(email: string | undefined) {
  if (!email) return "??";
  const [name] = email.split("@");
  const cleaned = name.replaceAll(/[^a-zA-Z0-9]/g, "");
  return cleaned.slice(0, 2).toUpperCase().padEnd(2, "?");
}

export function TripCollaboratorsPanel(props: {
  tripId: number;
  ownerId?: string;
  currentUserId: string | null;
  collaborators: TripCollaborator[];
  isOwner: boolean;
}) {
  const { toast } = useToast();
  const [pendingRemoval, setPendingRemoval] = useState<TripCollaborator | null>(null);

  const inviteMutation = useInviteTripCollaborator(props.tripId);
  const updateRoleMutation = useUpdateTripCollaboratorRole(props.tripId);
  const removeMutation = useRemoveTripCollaborator(props.tripId);

  const canManage = props.isOwner;
  const isCurrentUserOwner =
    props.currentUserId !== null &&
    typeof props.ownerId === "string" &&
    props.currentUserId === props.ownerId;

  const form = useZodForm({
    defaultValues: { email: "", role: "viewer" as const },
    schema: tripCollaboratorInviteSchema,
    validateMode: "onChange",
  });

  const handleCopyShareLink = async () => {
    if (typeof window === "undefined") return;

    const shareUrl = `${window.location.origin}/dashboard/trips/${props.tripId}`;
    await copyToClipboardWithToast(shareUrl, toast, {
      success: { description: "Share link copied to clipboard", title: "Link Copied" },
    });
  };

  const handleInvite = form.handleSubmitSafe(async (values) => {
    try {
      const result = await inviteMutation.mutateAsync(values);
      form.reset({ email: "", role: values.role });

      toast({
        description: result.invited
          ? "Invite email sent. They’ll have access after accepting."
          : "Collaborator added to this trip.",
        title: "Collaborator Invited",
      });
    } catch (error) {
      toast({
        description:
          error instanceof Error ? error.message : "Unable to invite collaborator",
        title: "Invite Failed",
        variant: "destructive",
      });
    }
  });

  const handleUpdateRole = async (
    collaborator: TripCollaborator,
    role: TripCollaboratorRole
  ) => {
    try {
      await updateRoleMutation.mutateAsync({
        collaboratorUserId: collaborator.userId,
        payload: { role },
      });

      toast({
        description: `Updated role for ${collaborator.userEmail ?? "collaborator"}.`,
        title: "Role Updated",
      });
    } catch (error) {
      toast({
        description: error instanceof Error ? error.message : "Unable to update role",
        title: "Update Failed",
        variant: "destructive",
      });
    }
  };

  const confirmRemoval = async () => {
    if (!pendingRemoval) return;
    try {
      await removeMutation.mutateAsync({ collaboratorUserId: pendingRemoval.userId });

      toast({
        description: `${pendingRemoval.userEmail ?? "Collaborator"} removed from this trip.`,
        title: "Collaborator Removed",
      });
    } catch (error) {
      toast({
        description:
          error instanceof Error ? error.message : "Unable to remove collaborator",
        title: "Removal Failed",
        variant: "destructive",
      });
    } finally {
      setPendingRemoval(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-lg border bg-gradient-to-br from-muted/40 to-background p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-1">
            <div className="text-sm font-medium">Share</div>
            <p className="text-xs text-muted-foreground">
              Copy a link for collaborators. Access still depends on invitation.
            </p>
          </div>

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleCopyShareLink}
          >
            <LinkIcon className="mr-2 h-4 w-4" />
            Copy Link
          </Button>
        </div>
      </div>

      <Form {...form}>
        <form onSubmit={handleInvite} className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-5">
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem className="sm:col-span-3">
                  <FormLabel>Email</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="teammate@example.com"
                      autoComplete="email"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="role"
              render={({ field }) => (
                <FormItem className="sm:col-span-1">
                  <FormLabel>Role</FormLabel>
                  <Select
                    value={field.value}
                    onValueChange={(value) => {
                      const parsed = tripCollaboratorRoleSchema.safeParse(value);
                      if (parsed.success) field.onChange(parsed.data);
                    }}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select role" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="viewer">Viewer</SelectItem>
                      <SelectItem value="editor">Editor</SelectItem>
                      <SelectItem value="owner">Owner</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="sm:col-span-1 sm:pt-7">
              <Button
                type="submit"
                className="w-full"
                disabled={!canManage || inviteMutation.isPending}
              >
                {inviteMutation.isPending ? (
                  <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <UserPlusIcon className="mr-2 h-4 w-4" />
                )}
                Invite
              </Button>
            </div>
          </div>

          {!canManage && (
            <div className="text-xs text-muted-foreground">
              Only the trip owner can invite collaborators.
            </div>
          )}
        </form>
      </Form>

      <Separator />

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-sm font-medium">People</div>
          <Badge variant="secondary">
            {props.collaborators.length} collaborator
            {props.collaborators.length === 1 ? "" : "s"}
          </Badge>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between rounded-lg border bg-muted/20 px-3 py-2">
            <div className="flex items-center gap-3">
              <Avatar className="h-8 w-8 ring-1 ring-border">
                <AvatarFallback>{isCurrentUserOwner ? "ME" : "OW"}</AvatarFallback>
              </Avatar>
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">
                  {isCurrentUserOwner ? "You" : "Trip Owner"}
                </div>
                <div className="text-xs text-muted-foreground">Owner</div>
              </div>
            </div>
            <Badge variant="outline" className="border-amber-500/40 text-amber-700">
              Owner
            </Badge>
          </div>

          {props.collaborators.map((collaborator) => {
            const roleMeta = ROLE_META[collaborator.role];
            const Icon = roleMeta.icon;
            const isSelf = collaborator.userId === props.currentUserId;
            return (
              <div
                key={collaborator.id}
                className="flex flex-col gap-3 rounded-lg border bg-background px-3 py-2 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex items-center gap-3">
                  <Avatar className="h-8 w-8 ring-1 ring-border">
                    <AvatarFallback>
                      {GetInitialsFromEmail(collaborator.userEmail)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium">
                      {collaborator.userEmail ?? collaborator.userId}
                      {isSelf ? (
                        <span className="ml-2 text-xs text-muted-foreground">
                          (you)
                        </span>
                      ) : null}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Added{" "}
                      {collaborator.createdAt
                        ? new Date(collaborator.createdAt).toLocaleDateString()
                        : "recently"}
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-2 sm:justify-end">
                  {canManage ? (
                    <Select
                      value={collaborator.role}
                      onValueChange={(value) => {
                        const parsed = tripCollaboratorRoleSchema.safeParse(value);
                        if (!parsed.success) return;
                        handleUpdateRole(collaborator, parsed.data);
                      }}
                      disabled={updateRoleMutation.isPending}
                    >
                      <SelectTrigger className="h-9 w-[140px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="viewer">Viewer</SelectItem>
                        <SelectItem value="editor">Editor</SelectItem>
                        <SelectItem value="owner">Owner</SelectItem>
                      </SelectContent>
                    </Select>
                  ) : (
                    <Badge className={cn("gap-1", roleMeta.badge)}>
                      <Icon className="h-3 w-3" />
                      {roleMeta.label}
                    </Badge>
                  )}

                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => setPendingRemoval(collaborator)}
                    disabled={removeMutation.isPending || (!canManage && !isSelf)}
                  >
                    <Trash2Icon className="mr-2 h-4 w-4" />
                    {isSelf && !canManage ? "Leave" : "Remove"}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <AlertDialog
        open={pendingRemoval !== null}
        onOpenChange={(open) => !open && setPendingRemoval(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {pendingRemoval?.userId === props.currentUserId
                ? "Leave trip?"
                : "Remove collaborator?"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {pendingRemoval?.userId === props.currentUserId
                ? "You will lose access to this trip."
                : "They will lose access to this trip."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={removeMutation.isPending}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault();
                confirmRemoval().catch(() => undefined);
              }}
              disabled={removeMutation.isPending}
              aria-busy={removeMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {removeMutation.isPending ? (
                <>
                  <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />
                  Removing...
                </>
              ) : (
                "Confirm"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
