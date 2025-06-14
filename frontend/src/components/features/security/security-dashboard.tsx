"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/contexts/auth-context";
import { useApiKeys } from "@/hooks/use-api-keys";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Eye,
  Globe,
  Info,
  Key,
  Lock,
  Monitor,
  RefreshCw,
  Settings,
  Shield,
  Smartphone,
  UserCheck,
} from "lucide-react";
import { useEffect, useState } from "react";

interface SecurityEvent {
  id: string;
  type:
    | "login_success"
    | "login_failure"
    | "logout"
    | "password_change"
    | "api_key_created"
    | "suspicious_activity";
  description: string;
  timestamp: string;
  ip_address: string;
  location?: string;
  device?: string;
  risk_level: "low" | "medium" | "high";
}

interface ActiveSession {
  id: string;
  device: string;
  browser: string;
  location: string;
  ip_address: string;
  last_activity: string;
  is_current: boolean;
}

interface SecurityMetrics {
  last_login: string;
  failed_login_attempts: number;
  active_sessions: number;
  api_keys_count: number;
  oauth_connections: string[];
  security_score: number;
}

export function SecurityDashboard() {
  const { user } = useAuth();
  const apiKeysQuery = useApiKeys();
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [metrics, setMetrics] = useState<SecurityMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Mock data for demonstration - replace with real API calls
  useEffect(() => {
    const loadSecurityData = async () => {
      try {
        // Simulate API calls
        await new Promise((resolve) => setTimeout(resolve, 1000));

        // Mock security events
        setEvents([
          {
            id: "1",
            type: "login_success",
            description: "Successful login",
            timestamp: "2025-06-11T10:30:00Z",
            ip_address: "192.168.1.100",
            location: "San Francisco, CA",
            device: "Chrome on MacOS",
            risk_level: "low",
          },
          {
            id: "2",
            type: "api_key_created",
            description: "New OpenAI API key added",
            timestamp: "2025-06-10T14:15:00Z",
            ip_address: "192.168.1.100",
            location: "San Francisco, CA",
            device: "Chrome on MacOS",
            risk_level: "low",
          },
          {
            id: "3",
            type: "login_failure",
            description: "Failed login attempt",
            timestamp: "2025-06-09T08:45:00Z",
            ip_address: "203.0.113.1",
            location: "Unknown",
            device: "Unknown",
            risk_level: "medium",
          },
        ]);

        // Mock active sessions
        setSessions([
          {
            id: "1",
            device: "MacBook Pro",
            browser: "Chrome 120.0",
            location: "San Francisco, CA",
            ip_address: "192.168.1.100",
            last_activity: "2025-06-11T10:30:00Z",
            is_current: true,
          },
          {
            id: "2",
            device: "iPhone 15",
            browser: "Safari Mobile",
            location: "San Francisco, CA",
            ip_address: "192.168.1.101",
            last_activity: "2025-06-11T09:15:00Z",
            is_current: false,
          },
        ]);

        // Mock security metrics
        setMetrics({
          last_login: "2025-06-11T10:30:00Z",
          failed_login_attempts: 1,
          active_sessions: 2,
          api_keys_count: Array.isArray(apiKeysQuery.data?.keys)
            ? apiKeysQuery.data.keys.length
            : 0,
          oauth_connections: ["google", "github"],
          security_score: 85,
        });

        setIsLoading(false);
      } catch (error) {
        console.error("Failed to load security data:", error);
        setIsLoading(false);
      }
    };

    loadSecurityData();
  }, [apiKeysQuery.data]);

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
      case "api_key_created":
        return <Key className="h-4 w-4 text-purple-600" />;
      case "suspicious_activity":
        return <AlertTriangle className="h-4 w-4 text-red-600" />;
      default:
        return <Info className="h-4 w-4 text-gray-600" />;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const handleTerminateSession = async (sessionId: string) => {
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
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
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
            metrics.security_score >= 80
              ? "border-green-200 bg-green-50"
              : "border-yellow-200 bg-yellow-50"
          }
        >
          <Shield
            className={`h-4 w-4 ${metrics.security_score >= 80 ? "text-green-600" : "text-yellow-600"}`}
          />
          <AlertDescription>
            <div className="flex items-center justify-between">
              <span>
                Security Score: <strong>{metrics.security_score}/100</strong>
                {metrics.security_score >= 80 ? " - Excellent" : " - Good"}
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
                    {formatTimestamp(metrics.last_login)}
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
                  <p className="text-2xl font-bold">{metrics.active_sessions}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <Key className="h-4 w-4 text-muted-foreground" />
                <div className="ml-2">
                  <p className="text-sm font-medium">API Keys</p>
                  <p className="text-2xl font-bold">{metrics.api_keys_count}</p>
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
                  <p className="text-2xl font-bold">{metrics.failed_login_attempts}</p>
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
                        {session.is_current && (
                          <Badge variant="outline" className="text-xs">
                            Current
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">{session.browser}</p>
                      <p className="text-xs text-muted-foreground">
                        {session.location} • {formatTimestamp(session.last_activity)}
                      </p>
                    </div>
                  </div>
                  {!session.is_current && (
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
                        className={`text-xs ${getRiskColor(event.risk_level)}`}
                      >
                        {event.risk_level}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {event.location || "Unknown location"} •{" "}
                      {formatTimestamp(event.timestamp)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      IP: {event.ip_address}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* OAuth Connections */}
      {metrics && metrics.oauth_connections.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <UserCheck className="mr-2 h-5 w-5" />
              Connected Accounts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex space-x-4">
              {metrics.oauth_connections.map((provider) => (
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
            {metrics && metrics.security_score < 90 && (
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
                <h4 className="font-medium">Review API Keys</h4>
                <p className="text-sm text-muted-foreground">
                  Regularly audit and rotate your API keys.
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
