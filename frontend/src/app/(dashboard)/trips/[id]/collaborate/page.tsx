"use client";

import {
  Clock,
  Copy,
  Crown,
  Edit,
  Eye,
  Mail,
  Share2,
  Trash2,
  UserPlus,
  Users,
} from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";
import { ConnectionStatusMonitor } from "@/components/features/realtime/connection-status-monitor";
import {
  CollaborationIndicator,
  OptimisticTripUpdates,
} from "@/components/features/realtime/optimistic-trip-updates";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/components/ui/use-toast";
import { useAuth } from "@/contexts/auth-context";
import {
  useTripCollaboration,
  useTripWithRealtime,
} from "@/hooks/use-trips-with-realtime";

interface Collaborator {
  id: string;
  user_id: string;
  trip_id: string;
  email: string;
  name?: string;
  role: "owner" | "editor" | "viewer";
  status: "pending" | "accepted" | "declined";
  permissions: {
    can_edit: boolean;
    can_invite: boolean;
    can_delete: boolean;
  };
  invited_at: string;
  accepted_at?: string;
}

export default function TripCollaborationPage() {
  const params = useParams();
  const tripId = params.id as string;
  const { toast } = useToast();
  const { user } = useAuth();

  const {
    trip,
    isConnected,
    connectionErrors: _connectionErrors,
  } = useTripWithRealtime(Number.parseInt(tripId, 10));

  // Type assertion for trip data
  const typedTrip = trip as {
    title?: string;
    name?: string;
    visibility?: string;
  } | null;
  useTripCollaboration(tripId); // Initialize collaboration state

  const currentUserId = user?.id;

  const [inviteEmail, setInviteEmail] = useState("");
  const [isInviting, setIsInviting] = useState(false);

  // Mock collaborators data - in real implementation, this would come from a hook
  const [collaborators] = useState<Collaborator[]>([
    {
      id: "1",
      user_id: "user-123",
      trip_id: tripId,
      email: "alice@example.com",
      name: "Alice Johnson",
      role: "owner",
      status: "accepted",
      permissions: {
        can_edit: true,
        can_invite: true,
        can_delete: true,
      },
      invited_at: new Date().toISOString(),
      accepted_at: new Date().toISOString(),
    },
    {
      id: "2",
      user_id: "user-456",
      trip_id: tripId,
      email: "bob@example.com",
      name: "Bob Smith",
      role: "editor",
      status: "accepted",
      permissions: {
        can_edit: true,
        can_invite: false,
        can_delete: false,
      },
      invited_at: new Date(Date.now() - 86400000).toISOString(),
      accepted_at: new Date(Date.now() - 86400000).toISOString(),
    },
    {
      id: "3",
      user_id: "user-789",
      trip_id: tripId,
      email: "charlie@example.com",
      role: "viewer",
      status: "pending",
      permissions: {
        can_edit: false,
        can_invite: false,
        can_delete: false,
      },
      invited_at: new Date(Date.now() - 3600000).toISOString(),
    },
  ]);

  const handleInviteCollaborator = async () => {
    if (!inviteEmail.trim()) {
      toast({
        title: "Email Required",
        description: "Please enter an email address to invite.",
        variant: "destructive",
      });
      return;
    }

    setIsInviting(true);
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));

      toast({
        title: "Invitation Sent",
        description: `Invitation sent to ${inviteEmail}`,
      });

      setInviteEmail("");
    } catch (_error) {
      toast({
        title: "Invitation Failed",
        description: "Failed to send invitation. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsInviting(false);
    }
  };

  const handleCopyShareLink = () => {
    const shareUrl = `${window.location.origin}/trips/${tripId}/share`;
    navigator.clipboard.writeText(shareUrl);
    toast({
      title: "Link Copied",
      description: "Share link copied to clipboard",
    });
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case "owner":
        return <Crown className="h-4 w-4 text-yellow-500" />;
      case "editor":
        return <Edit className="h-4 w-4 text-blue-500" />;
      case "viewer":
        return <Eye className="h-4 w-4 text-gray-500" />;
      default:
        return <Users className="h-4 w-4" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "accepted":
        return (
          <Badge variant="default" className="bg-green-500">
            Active
          </Badge>
        );
      case "pending":
        return <Badge variant="secondary">Pending</Badge>;
      case "declined":
        return <Badge variant="destructive">Declined</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  if (!typedTrip) {
    return (
      <div className="container mx-auto py-8">
        <Card>
          <CardContent className="text-center py-12">
            <h2 className="text-xl font-semibold mb-2">Trip not found</h2>
            <p className="text-muted-foreground">
              The trip you're looking for doesn't exist or you don't have access to it.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">
            Collaborate on {typedTrip.title || typedTrip.name}
          </h1>
          <p className="text-muted-foreground">
            Manage collaborators and real-time editing
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <ConnectionStatusMonitor />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Real-time Trip Editing */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Edit className="h-5 w-5" />
                <span>Live Trip Editing</span>
              </CardTitle>
              <CardDescription>
                Edit trip details with real-time collaboration
              </CardDescription>
            </CardHeader>
            <CardContent>
              <OptimisticTripUpdates tripId={Number.parseInt(tripId, 10)} />
            </CardContent>
          </Card>

          {/* Collaborators Management */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Users className="h-5 w-5" />
                <span>Collaborators</span>
                <Badge variant="secondary">{collaborators.length}</Badge>
              </CardTitle>
              <CardDescription>
                Manage who can access and edit this trip
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-6">
              {/* Invite New Collaborator */}
              <div className="space-y-4">
                <Label htmlFor="invite-email">Invite by Email</Label>
                <div className="flex space-x-2">
                  <Input
                    id="invite-email"
                    type="email"
                    placeholder="Enter email address..."
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        handleInviteCollaborator();
                      }
                    }}
                  />
                  <Button onClick={handleInviteCollaborator} disabled={isInviting}>
                    <UserPlus className="h-4 w-4 mr-2" />
                    {isInviting ? "Inviting..." : "Invite"}
                  </Button>
                </div>
              </div>

              <Separator />

              {/* Share Link */}
              <div className="space-y-4">
                <Label>Share Link</Label>
                <div className="flex space-x-2">
                  <Input
                    readOnly
                    value={`${typeof window !== "undefined" ? window.location.origin : ""}/trips/${tripId}/share`}
                    className="bg-muted"
                  />
                  <Button variant="outline" onClick={handleCopyShareLink}>
                    <Copy className="h-4 w-4 mr-2" />
                    Copy
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Anyone with this link can view the trip details
                </p>
              </div>

              <Separator />

              {/* Collaborator List */}
              <div className="space-y-4">
                <Label>Current Collaborators</Label>
                <div className="space-y-3">
                  {collaborators.map((collaborator) => (
                    <div
                      key={collaborator.id}
                      className="flex items-center justify-between p-3 rounded-lg border"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                          <Mail className="h-4 w-4" />
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="font-medium">
                              {collaborator.name || collaborator.email}
                            </span>
                            {collaborator.user_id === currentUserId && (
                              <Badge variant="outline" className="text-xs">
                                You
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                            <span>{collaborator.email}</span>
                            <span>•</span>
                            <div className="flex items-center space-x-1">
                              {getRoleIcon(collaborator.role)}
                              <span className="capitalize">{collaborator.role}</span>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        {getStatusBadge(collaborator.status)}

                        {collaborator.role !== "owner" && (
                          <Button variant="ghost" size="sm">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Active Collaborators */}
          <CollaborationIndicator tripId={Number.parseInt(tripId, 10)} />

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Clock className="h-5 w-5" />
                <span>Recent Activity</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="text-sm">
                  <div className="font-medium">Alice Johnson</div>
                  <div className="text-muted-foreground">Updated trip budget</div>
                  <div className="text-xs text-muted-foreground">2 minutes ago</div>
                </div>
                <Separator />
                <div className="text-sm">
                  <div className="font-medium">Bob Smith</div>
                  <div className="text-muted-foreground">Added destination: Rome</div>
                  <div className="text-xs text-muted-foreground">1 hour ago</div>
                </div>
                <Separator />
                <div className="text-sm">
                  <div className="font-medium">You</div>
                  <div className="text-muted-foreground">Invited Charlie Brown</div>
                  <div className="text-xs text-muted-foreground">2 hours ago</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Trip Settings */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Share2 className="h-5 w-5" />
                <span>Sharing Settings</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Visibility</Label>
                <Badge variant="secondary">{typedTrip.visibility || "Private"}</Badge>
                <p className="text-xs text-muted-foreground">
                  {typedTrip.visibility === "public"
                    ? "Anyone can view this trip"
                    : typedTrip.visibility === "shared"
                      ? "Only invited collaborators can view"
                      : "Only you can view this trip"}
                </p>
              </div>

              <div className="space-y-2">
                <Label>Real-time Updates</Label>
                <Badge variant={isConnected ? "default" : "destructive"}>
                  {isConnected ? "Connected" : "Disconnected"}
                </Badge>
                <p className="text-xs text-muted-foreground">
                  Changes are synced automatically when connected
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
