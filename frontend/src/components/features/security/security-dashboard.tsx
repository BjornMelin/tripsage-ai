/**
 * @fileoverview Security dashboard component.
 *
 * Displays security metrics, active sessions, security events, OAuth accounts,
 * and security recommendations.
 */

"use client";

import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Info,
  Lock,
  Monitor,
  RefreshCw,
  Settings,
  Shield,
  Smartphone,
  UserCheck,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Represents a security-related event in the user's account.
 */
interface SecurityEvent {
  /** Unique identifier for the security event. */
  id: string;
  /** Type of security event that occurred. */
  type:
    | "login_success"
    | "login_failure"
    | "logout"
    | "password_change"
    | "mfa_enabled"
    | "suspicious_activity";
  /** Human-readable description of the event. */
  description: string;
  /** ISO timestamp when the event occurred. */
  timestamp: string;
  /** IP address associated with the event. */
  ipAddress: string;
  /** Optional location information derived from IP. */
  location?: string;
  /** Optional device/browser information. */
  device?: string;
  /** Risk level assessment of the event. */
  riskLevel: "low" | "medium" | "high";
}

/**
 * Represents an active user session.
 */
interface ActiveSession {
  /** Unique identifier for the session. */
  id: string;
  /** Device name or type. */
  device: string;
  /** Browser and version information. */
  browser: string;
  /** Location derived from IP address. */
  location: string;
  /** IP address of the session. */
  ipAddress: string;
  /** ISO timestamp of last activity. */
  lastActivity: string;
  /** Whether this is the current user's session. */
  isCurrent: boolean;
}

/**
 * Security metrics and statistics for the user account.
 */
interface SecurityMetrics {
  /** ISO timestamp of the last successful login. */
  lastLogin: string;
  /** Number of failed login attempts in the last 24 hours. */
  failedLoginAttempts: number;
  /** Number of currently active sessions. */
  activeSessions: number;
  /** Number of trusted devices registered. */
  trustedDevices: number;
  /** List of connected OAuth providers. */
  oauthConnections: string[];
  /** Overall security score out of 100. */
  securityScore: number;
}

/**
 * Security dashboard component.
 *
 * Displays security metrics, active sessions, security events, and recommendations.
 * Aggregates Supabase-authenticated activity metadata.
 *
 * @returns The security dashboard JSX element
 */
export function SecurityDashboard() {
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [metrics, setMetrics] = useState<SecurityMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Mock data for demonstration - replace with real API calls
  useEffect(() => {
    /**
     * Loads security data from mock API endpoints.
     */
    const loadSecurityData = async () => {
      try {
        // Simulate API calls
        await new Promise((resolve) => setTimeout(resolve, 1000));

        // Mock security events
        setEvents([
          {
            description: "Successful login",
            device: "Chrome on MacOS",
            id: "1",
            ipAddress: "192.168.1.100",
            location: "San Francisco, CA",
            riskLevel: "low",
            timestamp: "2025-06-11T10:30:00Z",
            type: "login_success",
          },
          {
            description: "Multi-factor authentication enabled",
            device: "Chrome on MacOS",
            id: "2",
            ipAddress: "192.168.1.100",
            location: "San Francisco, CA",
            riskLevel: "low",
            timestamp: "2025-06-10T14:15:00Z",
            type: "mfa_enabled",
          },
          {
            description: "Failed login attempt",
            device: "Unknown",
            id: "3",
            ipAddress: "203.0.113.1",
            location: "Unknown",
            riskLevel: "medium",
            timestamp: "2025-06-09T08:45:00Z",
            type: "login_failure",
          },
        ]);

        // Mock active sessions
        setSessions([
          {
            browser: "Chrome 120.0",
            device: "MacBook Pro",
            id: "1",
            ipAddress: "192.168.1.100",
            isCurrent: true,
            lastActivity: "2025-06-11T10:30:00Z",
            location: "San Francisco, CA",
          },
          {
            browser: "Safari Mobile",
            device: "iPhone 15",
            id: "2",
            ipAddress: "192.168.1.101",
            isCurrent: false,
            lastActivity: "2025-06-11T09:15:00Z",
            location: "San Francisco, CA",
          },
        ]);

        // Mock security metrics
        setMetrics({
          activeSessions: 2,
          failedLoginAttempts: 1,
          lastLogin: "2025-06-11T10:30:00Z",
          oauthConnections: ["google", "github"],
          securityScore: 85,
          trustedDevices: 2,
        });

        setIsLoading(false);
      } catch (error) {
        console.error("Failed to load security data:", error);
        setIsLoading(false);
      }
    };

    loadSecurityData();
  }, []);

  /**
   * Returns CSS classes for risk level styling.
   *
   * @param level - Risk level (low, medium, high)
   * @returns CSS classes for the risk level
   */
  const getRiskColor = (level: string) => {
    switch (level) {
      case "high":
        return "text-red-600 bg-red-50 border-red-200";
      case "medium":
        return "text-yellow-600 bg-yellow-50 border-yellow-200";
      case "low":
        return "text-green-600 bg-green-50 border-green-200";
      default:
        return "text-gray-600 bg-gray-50 border-gray-200";
    }
  };

  /**
   * Returns the appropriate icon component for security event types.
   *
   * @param type - Security event type
   * @returns Icon component for the event type
   */
  const getEventIcon = (type: string) => {
    switch (type) {
      case "login_success":
        return <CheckCircle2 className="h-4 w-4 text-green-600" />;
      case "login_failure":
        return <AlertTriangle className="h-4 w-4 text-red-600" />;
      case "logout":
        return <Shield className="h-4 w-4 text-blue-600" />;
      case "password_change":
        return <Lock className="h-4 w-4 text-blue-600" />;
      case "mfa_enabled":
        return <Shield className="h-4 w-4 text-purple-600" />;
      case "suspicious_activity":
        return <AlertTriangle className="h-4 w-4 text-red-600" />;
      default:
        return <Info className="h-4 w-4 text-gray-600" />;
    }
  };

  /**
   * Formats ISO timestamp for display.
   *
   * @param timestamp - ISO timestamp string
   * @returns Formatted timestamp string
   */
  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  /**
   * Terminates an active user session.
   *
   * @param sessionId - ID of the session to terminate
   */
  const handleTerminateSession = (sessionId: string) => {
    try {
      // TODO: Implement session termination
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    } catch (error) {
      console.error("Failed to terminate session:", error);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-muted animate-pulse rounded" />
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {["metric-1", "metric-2", "metric-3", "metric-4"].map((id) => (
            <Card key={id}>
              <CardContent className="p-6">
                <div className="h-4 bg-muted animate-pulse rounded mb-2" />
                <div className="h-8 bg-muted animate-pulse rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Security Dashboard</h2>
          <p className="text-muted-foreground">
            Monitor your account security and activity
          </p>
        </div>
        <Button variant="outline" size="sm">
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Security Score */}
      {metrics && (
        <Alert
          className={
            metrics.securityScore >= 80
              ? "border-green-200 bg-green-50"
              : "border-yellow-200 bg-yellow-50"
          }
        >
          <Shield
            className={`h-4 w-4 ${metrics.securityScore >= 80 ? "text-green-600" : "text-yellow-600"}`}
          />
          <AlertDescription>
            <div className="flex items-center justify-between">
              <span>
                Security Score: <strong>{metrics.securityScore}/100</strong>
                {metrics.securityScore >= 80 ? " - Excellent" : " - Good"}
              </span>
              <Button variant="ghost" size="sm">
                <Settings className="h-4 w-4" />
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* Security Metrics */}
      {metrics && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <div className="ml-2">
                  <p className="text-sm font-medium">Last Login</p>
                  <p className="text-2xl font-bold">
                    {formatTimestamp(metrics.lastLogin)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <Monitor className="h-4 w-4 text-muted-foreground" />
                <div className="ml-2">
                  <p className="text-sm font-medium">Active Sessions</p>
                  <p className="text-2xl font-bold">{metrics.activeSessions}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <Smartphone className="h-4 w-4 text-muted-foreground" />
                <div className="ml-2">
                  <p className="text-sm font-medium">Trusted Devices</p>
                  <p className="text-2xl font-bold">{metrics.trustedDevices}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <AlertTriangle className="h-4 w-4 text-muted-foreground" />
                <div className="ml-2">
                  <p className="text-sm font-medium">Failed Logins (24h)</p>
                  <p className="text-2xl font-bold">{metrics.failedLoginAttempts}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Active Sessions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Monitor className="mr-2 h-5 w-5" />
              Active Sessions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <Smartphone className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <div className="flex items-center space-x-2">
                        <p className="font-medium">{session.device}</p>
                        {session.isCurrent && (
                          <Badge variant="outline" className="text-xs">
                            Current
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">{session.browser}</p>
                      <p className="text-xs text-muted-foreground">
                        {session.location} • {formatTimestamp(session.lastActivity)}
                      </p>
                    </div>
                  </div>
                  {!session.isCurrent && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleTerminateSession(session.id)}
                    >
                      Terminate
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Security Events */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Activity className="mr-2 h-5 w-5" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {events.map((event) => (
                <div
                  key={event.id}
                  className="flex items-start space-x-3 p-3 border rounded-lg"
                >
                  {getEventIcon(event.type)}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className="font-medium">{event.description}</p>
                      <Badge
                        variant="outline"
                        className={`text-xs ${getRiskColor(event.riskLevel)}`}
                      >
                        {event.riskLevel}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {event.location || "Unknown location"} •{" "}
                      {formatTimestamp(event.timestamp)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      IP: {event.ipAddress}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* OAuth Connections */}
      {metrics && metrics.oauthConnections.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <UserCheck className="mr-2 h-5 w-5" />
              Connected Accounts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex space-x-4">
              {metrics.oauthConnections.map((provider) => (
                <div
                  key={provider}
                  className="flex items-center space-x-2 p-3 border rounded-lg"
                >
                  <div className="w-8 h-8 bg-muted rounded flex items-center justify-center">
                    {provider === "google" && (
                      <span className="text-sm font-bold">G</span>
                    )}
                    {provider === "github" && (
                      <span className="text-sm font-bold">GH</span>
                    )}
                  </div>
                  <div>
                    <p className="font-medium capitalize">{provider}</p>
                    <p className="text-xs text-muted-foreground">Connected</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Security Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Shield className="mr-2 h-5 w-5" />
            Security Recommendations
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {metrics && metrics.securityScore < 90 && (
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  Enable two-factor authentication to improve your security score.
                </AlertDescription>
              </Alert>
            )}

            <div className="grid gap-3 md:grid-cols-2">
              <div className="p-3 border rounded-lg">
                <h4 className="font-medium">Regular Password Updates</h4>
                <p className="text-sm text-muted-foreground">
                  Change your password every 90 days for optimal security.
                </p>
              </div>

              <div className="p-3 border rounded-lg">
                <h4 className="font-medium">Enable MFA</h4>
                <p className="text-sm text-muted-foreground">
                  Add multi-factor authentication to protect your account.
                </p>
              </div>

              <div className="p-3 border rounded-lg">
                <h4 className="font-medium">Monitor Sessions</h4>
                <p className="text-sm text-muted-foreground">
                  Terminate unknown or inactive sessions.
                </p>
              </div>

              <div className="p-3 border rounded-lg">
                <h4 className="font-medium">Enable Notifications</h4>
                <p className="text-sm text-muted-foreground">
                  Get alerts for suspicious activity.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
