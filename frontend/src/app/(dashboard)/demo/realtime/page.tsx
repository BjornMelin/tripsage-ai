"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Activity,
  CheckCircle,
  FileText,
  MessageSquare,
  Upload,
  Users,
  Wifi,
  Zap,
} from "lucide-react";
import { useState } from "react";

import { ConnectionStatusMonitor } from "@/components/features/realtime/connection-status-monitor";
import {
  CollaborationIndicator,
  OptimisticTripUpdates,
} from "@/components/features/realtime/optimistic-trip-updates";
import { useTripsWithRealtime } from "@/hooks/use-trips-with-realtime";

/**
 * Demonstration page showcasing all real-time Supabase integration features
 */
export default function RealtimeDemoPage() {
  const { trips, realtimeStatus } = useTripsWithRealtime();
  const [activeTab, setActiveTab] = useState("overview");

  const features = [
    {
      id: "direct-sdk",
      title: "Direct Supabase SDK Integration",
      description: "Replaced custom API calls with direct Supabase client usage",
      status: "completed",
      icon: <Zap className="h-5 w-5" />,
      details: [
        "Trip store uses Supabase client directly",
        "Real-time data fetching and mutations",
        "Type-safe database operations",
        "Automatic query optimization",
      ],
    },
    {
      id: "realtime-subscriptions",
      title: "Real-time Subscriptions",
      description: "Live updates for trips, chat messages, and collaboration",
      status: "completed",
      icon: <Activity className="h-5 w-5" />,
      details: [
        "Trip collaboration updates",
        "Live editing indicators",
        "Automatic conflict resolution",
        "Connection status monitoring",
      ],
    },
    {
      id: "optimistic-updates",
      title: "Optimistic Updates",
      description: "Instant UI feedback with automatic rollback on errors",
      status: "completed",
      icon: <CheckCircle className="h-5 w-5" />,
      details: [
        "Immediate UI response",
        "Error handling with rollback",
        "Loading state management",
        "Success/failure notifications",
      ],
    },
    {
      id: "connection-monitoring",
      title: "Connection Status Monitoring",
      description: "Real-time connectivity status and reconnection handling",
      status: "completed",
      icon: <Wifi className="h-5 w-5" />,
      details: [
        "Connection health visualization",
        "Automatic reconnection attempts",
        "Offline mode detection",
        "Error state handling",
      ],
    },
    {
      id: "chat-updates",
      title: "Real-time Chat Messages",
      description: "Live chat message updates and typing indicators",
      status: "pending",
      icon: <MessageSquare className="h-5 w-5" />,
      details: [
        "Instant message delivery",
        "Typing indicators",
        "Message status tracking",
        "Infinite scroll pagination",
      ],
    },
    {
      id: "file-storage",
      title: "File Upload & Storage",
      description: "Real-time file upload progress and storage management",
      status: "completed",
      icon: <Upload className="h-5 w-5" />,
      details: [
        "Progress tracking",
        "Virus scanning integration",
        "Multiple file uploads",
        "Storage quotas",
      ],
    },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-500";
      case "pending":
        return "bg-yellow-500";
      case "in-progress":
        return "bg-blue-500";
      default:
        return "bg-gray-500";
    }
  };

  return (
    <div className="container mx-auto py-8 space-y-8">
      {/* Header */}
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold">Real-time Supabase Integration Demo</h1>
        <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
          Showcasing direct Supabase SDK usage, real-time subscriptions, optimistic
          updates, and comprehensive connection monitoring for the TripSage platform.
        </p>
        <div className="flex justify-center">
          <ConnectionStatusMonitor />
        </div>
      </div>

      {/* Implementation Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Activity className="h-6 w-6" />
            <span>Implementation Status</span>
          </CardTitle>
          <CardDescription>
            Overview of all implemented real-time features and integrations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature) => (
              <Card key={feature.id} className="relative">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {feature.icon}
                      <span className="font-medium">{feature.title}</span>
                    </div>
                    <Badge
                      variant={feature.status === "completed" ? "default" : "secondary"}
                      className={
                        feature.status === "completed"
                          ? getStatusColor(feature.status)
                          : ""
                      }
                    >
                      {feature.status}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{feature.description}</p>
                </CardHeader>
                <CardContent className="pt-0">
                  <ul className="space-y-1">
                    {feature.details.map((detail) => (
                      <li key={`${feature.id}-${detail}`} className="flex items-start space-x-2 text-sm">
                        <CheckCircle className="h-3 w-3 mt-0.5 text-green-500 flex-shrink-0" />
                        <span>{detail}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Interactive Demos */}
      <Card>
        <CardHeader>
          <CardTitle>Interactive Demonstrations</CardTitle>
          <CardDescription>
            Try out the real-time features with live examples
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="trip-editing">Trip Editing</TabsTrigger>
              <TabsTrigger value="collaboration">Collaboration</TabsTrigger>
              <TabsTrigger value="connection">Connection</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                  <CardContent className="p-6 text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {trips.length}
                    </div>
                    <div className="text-sm text-muted-foreground">Active Trips</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-6 text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {realtimeStatus.isConnected ? "✓" : "✗"}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Real-time Status
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-6 text-center">
                    <div className="text-2xl font-bold text-purple-600">
                      {realtimeStatus.errors.length}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Connection Errors
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="text-center space-y-4">
                <h3 className="text-lg font-semibold">Real-time Features Active</h3>
                <div className="flex flex-wrap justify-center gap-2">
                  <Badge variant="default" className="bg-green-500">
                    Direct Supabase SDK
                  </Badge>
                  <Badge variant="default" className="bg-blue-500">
                    Real-time Subscriptions
                  </Badge>
                  <Badge variant="default" className="bg-purple-500">
                    Optimistic Updates
                  </Badge>
                  <Badge variant="default" className="bg-orange-500">
                    Connection Monitoring
                  </Badge>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="trip-editing" className="space-y-4">
              <div className="text-center mb-6">
                <h3 className="text-lg font-semibold mb-2">Real-time Trip Editing</h3>
                <p className="text-muted-foreground">
                  Edit trip details and see changes reflected instantly with optimistic
                  updates
                </p>
              </div>
              <OptimisticTripUpdates tripId={1} />
            </TabsContent>

            <TabsContent value="collaboration" className="space-y-4">
              <div className="text-center mb-6">
                <h3 className="text-lg font-semibold mb-2">Live Collaboration</h3>
                <p className="text-muted-foreground">
                  See who's currently editing and real-time activity updates
                </p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <CollaborationIndicator tripId={1} />
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Users className="h-5 w-5" />
                      <span>Collaboration Features</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center space-x-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span className="text-sm">Live editing indicators</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span className="text-sm">Real-time conflict resolution</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span className="text-sm">Activity feed updates</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span className="text-sm">Collaborative permissions</span>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="connection" className="space-y-4">
              <div className="text-center mb-6">
                <h3 className="text-lg font-semibold mb-2">Connection Monitoring</h3>
                <p className="text-muted-foreground">
                  Real-time connection status and health monitoring
                </p>
              </div>
              <div className="max-w-md mx-auto">
                <ConnectionStatusMonitor />
              </div>
              <Card>
                <CardHeader>
                  <CardTitle>Connection Features</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span className="text-sm">Real-time connectivity status</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span className="text-sm">Automatic reconnection attempts</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span className="text-sm">Offline mode detection</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span className="text-sm">Connection health percentage</span>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Technical Implementation Details */}
      <Card>
        <CardHeader>
          <CardTitle>Technical Implementation</CardTitle>
          <CardDescription>
            Key technical details and architectural decisions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <h4 className="font-semibold">Supabase Integration</h4>
              <ul className="space-y-2 text-sm">
                <li>• Direct Supabase client usage replacing custom API layer</li>
                <li>• Type-safe database operations with generated types</li>
                <li>• Real-time subscriptions with automatic reconnection</li>
                <li>• Row Level Security (RLS) policy integration</li>
                <li>• Optimized query patterns with caching</li>
              </ul>
            </div>

            <div className="space-y-4">
              <h4 className="font-semibold">Frontend Architecture</h4>
              <ul className="space-y-2 text-sm">
                <li>• React Query for state management and caching</li>
                <li>• Zustand store integration with Supabase</li>
                <li>• Optimistic updates with automatic rollback</li>
                <li>• Connection monitoring and error handling</li>
                <li>• TypeScript type safety throughout</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Next Steps */}
      <Card>
        <CardHeader>
          <CardTitle>Next Steps & Roadmap</CardTitle>
          <CardDescription>
            Planned enhancements and additional features
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <h4 className="font-semibold">Immediate Enhancements</h4>
            <ul className="space-y-2 text-sm">
              <li>• Complete real-time chat message implementation</li>
              <li>• Add query caching and pagination optimizations</li>
              <li>• Implement offline synchronization</li>
              <li>• Add comprehensive error boundaries</li>
            </ul>

            <h4 className="font-semibold">Future Features</h4>
            <ul className="space-y-2 text-sm">
              <li>• Real-time voice/video collaboration</li>
              <li>• Advanced conflict resolution algorithms</li>
              <li>• Mobile app synchronization</li>
              <li>• Performance analytics and monitoring</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
