"use client";

/**
 * Configuration Manager Component
 *
 * React component for managing agent configurations with real-time updates,
 * versioning, and performance tracking following 2025 best practices.
 */

import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  DollarSign,
  Eye,
  History,
  RotateCcw,
  Save,
  Settings,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
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
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";

// Types
interface AgentConfig {
  agent_type: string;
  temperature: number;
  max_tokens: number;
  top_p: number;
  timeout_seconds: number;
  model: string;
  updated_at: string;
  updated_by?: string;
  description?: string;
}

interface ConfigVersion {
  version_id: string;
  configuration: Record<string, any>;
  description?: string;
  created_at: string;
  created_by: string;
  is_current: boolean;
}

interface PerformanceMetrics {
  agent_type: string;
  average_response_time: number;
  success_rate: number;
  error_rate: number;
  token_usage: Record<string, number>;
  cost_estimate: number;
  sample_size: number;
}

const AGENT_TYPES = [
  {
    value: "budget_agent",
    label: "Budget Agent",
    description: "Handles budget optimization and expense tracking",
  },
  {
    value: "destination_research_agent",
    label: "Research Agent",
    description: "Researches destinations and attractions",
  },
  {
    value: "itinerary_agent",
    label: "Itinerary Agent",
    description: "Plans and optimizes travel itineraries",
  },
];

const MODEL_OPTIONS = [
  "gpt-4",
  "gpt-4-turbo",
  "gpt-4o",
  "gpt-4o-mini",
  "gpt-3.5-turbo",
];

export default function ConfigurationManager() {
  useRouter(); // For potential navigation
  const { toast } = useToast();

  // State management
  const [configs, setConfigs] = useState<Record<string, AgentConfig>>({});
  const [versions, setVersions] = useState<Record<string, ConfigVersion[]>>({});
  const [metrics, setMetrics] = useState<Record<string, PerformanceMetrics>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<string>("budget_agent");
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<
    "connecting" | "connected" | "disconnected"
  >("disconnected");

  // Form state
  const [editedConfig, setEditedConfig] = useState<Partial<AgentConfig>>({});
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // WebSocket connection for real-time updates
  useEffect(() => {
    const connectWebSocket = () => {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/api/config/ws`;

      const websocket = new WebSocket(wsUrl);

      websocket.onopen = () => {
        setConnectionStatus("connected");
        setWs(websocket);
        console.log("Configuration WebSocket connected");
      };

      websocket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          handleWebSocketMessage(message);
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
        }
      };

      websocket.onclose = () => {
        setConnectionStatus("disconnected");
        setWs(null);
        // Reconnect after 5 seconds
        setTimeout(connectWebSocket, 5000);
      };

      websocket.onerror = (error) => {
        console.error("Configuration WebSocket error:", error);
        setConnectionStatus("disconnected");
      };
    };

    setConnectionStatus("connecting");
    connectWebSocket();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback(
    (message: any) => {
      switch (message.type) {
        case "agent_config_updated":
          toast({
            title: "Configuration Updated",
            description: `${message.agent_type} configuration was updated by ${message.updated_by}`,
            variant: "default",
          });
          // Refresh the specific agent config
          loadAgentConfig(message.agent_type);
          break;

        case "agent_config_rolled_back":
          toast({
            title: "Configuration Rolled Back",
            description: `${message.agent_type} was rolled back to version ${message.version_id}`,
            variant: "default",
          });
          loadAgentConfig(message.agent_type);
          break;

        default:
          console.log("Unknown WebSocket message type:", message.type);
      }
    },
    [toast]
  );

  // Load initial data
  useEffect(() => {
    loadAllConfigs();
  }, []);

  const loadAllConfigs = async () => {
    setLoading(true);
    try {
      // Load configurations for all agent types
      for (const agentType of AGENT_TYPES) {
        await Promise.all([
          loadAgentConfig(agentType.value),
          loadVersionHistory(agentType.value),
          loadPerformanceMetrics(agentType.value),
        ]);
      }
    } catch (error) {
      console.error("Error loading configurations:", error);
      toast({
        title: "Error",
        description: "Failed to load configurations",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const loadAgentConfig = async (agentType: string) => {
    try {
      const response = await fetch(`/api/config/agents/${agentType}`);
      if (!response.ok) throw new Error("Failed to load config");

      const config = await response.json();
      setConfigs((prev) => ({ ...prev, [agentType]: config }));

      // Initialize edited config if this is the selected agent
      if (agentType === selectedAgent) {
        setEditedConfig(config);
        setHasUnsavedChanges(false);
      }
    } catch (error) {
      console.error(`Error loading config for ${agentType}:`, error);
    }
  };

  const loadVersionHistory = async (agentType: string) => {
    try {
      const response = await fetch(`/api/config/agents/${agentType}/versions?limit=10`);
      if (!response.ok) throw new Error("Failed to load versions");

      const versionList = await response.json();
      setVersions((prev) => ({ ...prev, [agentType]: versionList }));
    } catch (error) {
      console.error(`Error loading versions for ${agentType}:`, error);
    }
  };

  const loadPerformanceMetrics = async (agentType: string) => {
    try {
      // This would be implemented with actual metrics endpoint
      // For now, using placeholder data
      const mockMetrics: PerformanceMetrics = {
        agent_type: agentType,
        average_response_time: Math.random() * 2000 + 500,
        success_rate: 0.95 + Math.random() * 0.04,
        error_rate: Math.random() * 0.05,
        token_usage: {
          input_tokens: Math.floor(Math.random() * 10000),
          output_tokens: Math.floor(Math.random() * 5000),
        },
        cost_estimate: Math.random() * 10,
        sample_size: Math.floor(Math.random() * 1000) + 100,
      };

      setMetrics((prev) => ({ ...prev, [agentType]: mockMetrics }));
    } catch (error) {
      console.error(`Error loading metrics for ${agentType}:`, error);
    }
  };

  // Handle agent selection change
  const handleAgentChange = (agentType: string) => {
    if (hasUnsavedChanges) {
      if (
        !confirm("You have unsaved changes. Are you sure you want to switch agents?")
      ) {
        return;
      }
    }

    setSelectedAgent(agentType);
    const config = configs[agentType];
    if (config) {
      setEditedConfig(config);
      setHasUnsavedChanges(false);
    }
  };

  // Handle configuration field changes
  const handleConfigChange = (field: keyof AgentConfig, value: any) => {
    setEditedConfig((prev) => ({ ...prev, [field]: value }));
    setHasUnsavedChanges(true);
  };

  // Save configuration
  const saveConfiguration = async () => {
    if (!selectedAgent || !editedConfig) return;

    setSaving(selectedAgent);
    try {
      const response = await fetch(`/api/config/agents/${selectedAgent}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          temperature: editedConfig.temperature,
          max_tokens: editedConfig.max_tokens,
          top_p: editedConfig.top_p,
          timeout_seconds: editedConfig.timeout_seconds,
          model: editedConfig.model,
          description: editedConfig.description,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to save configuration");
      }

      const updatedConfig = await response.json();
      setConfigs((prev) => ({ ...prev, [selectedAgent]: updatedConfig }));
      setEditedConfig(updatedConfig);
      setHasUnsavedChanges(false);

      toast({
        title: "Configuration Saved",
        description: `${selectedAgent} configuration has been updated successfully`,
        variant: "default",
      });

      // Reload version history to show the new version
      await loadVersionHistory(selectedAgent);
    } catch (error) {
      console.error("Error saving configuration:", error);
      toast({
        title: "Save Failed",
        description:
          error instanceof Error ? error.message : "Failed to save configuration",
        variant: "destructive",
      });
    } finally {
      setSaving(null);
    }
  };

  // Rollback to version
  const rollbackToVersion = async (versionId: string) => {
    if (!selectedAgent) return;

    try {
      const response = await fetch(
        `/api/config/agents/${selectedAgent}/rollback/${versionId}`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to rollback");
      }

      await loadAgentConfig(selectedAgent);
      await loadVersionHistory(selectedAgent);

      toast({
        title: "Rollback Successful",
        description: `Configuration rolled back to version ${versionId}`,
        variant: "default",
      });
    } catch (error) {
      console.error("Error rolling back:", error);
      toast({
        title: "Rollback Failed",
        description:
          error instanceof Error ? error.message : "Failed to rollback configuration",
        variant: "destructive",
      });
    }
  };

  // Reset to defaults
  const resetToDefaults = () => {
    const currentConfig = configs[selectedAgent];
    if (currentConfig) {
      setEditedConfig(currentConfig);
      setHasUnsavedChanges(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const currentConfig = configs[selectedAgent];
  const currentVersions = versions[selectedAgent] || [];
  const currentMetrics = metrics[selectedAgent];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Agent Configuration</h1>
          <p className="text-muted-foreground">
            Manage AI agent parameters and monitor performance
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant={connectionStatus === "connected" ? "default" : "destructive"}>
            {connectionStatus === "connected" ? "Live Updates" : "Disconnected"}
          </Badge>
        </div>
      </div>

      {/* Agent Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Select Agent
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Select value={selectedAgent} onValueChange={handleAgentChange}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select an agent to configure" />
            </SelectTrigger>
            <SelectContent>
              {AGENT_TYPES.map((agent) => (
                <SelectItem key={agent.value} value={agent.value}>
                  <div>
                    <div className="font-medium">{agent.label}</div>
                    <div className="text-sm text-muted-foreground">
                      {agent.description}
                    </div>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {currentConfig && (
        <Tabs defaultValue="configuration" className="space-y-4">
          <TabsList>
            <TabsTrigger value="configuration">Configuration</TabsTrigger>
            <TabsTrigger value="performance">Performance</TabsTrigger>
            <TabsTrigger value="history">Version History</TabsTrigger>
          </TabsList>

          {/* Configuration Tab */}
          <TabsContent value="configuration" className="space-y-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Agent Parameters</CardTitle>
                  <CardDescription>
                    Configure the behavior and performance parameters for the selected
                    agent
                  </CardDescription>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={resetToDefaults}
                    disabled={!hasUnsavedChanges}
                  >
                    <RotateCcw className="h-4 w-4 mr-2" />
                    Reset
                  </Button>

                  <Button
                    onClick={saveConfiguration}
                    disabled={!hasUnsavedChanges || saving === selectedAgent}
                  >
                    {saving === selectedAgent ? (
                      <LoadingSpinner size="sm" className="mr-2" />
                    ) : (
                      <Save className="h-4 w-4 mr-2" />
                    )}
                    Save Changes
                  </Button>
                </div>
              </CardHeader>

              <CardContent className="space-y-6">
                {/* Model Selection */}
                <div className="space-y-2">
                  <Label htmlFor="model">Model</Label>
                  <Select
                    value={editedConfig.model || ""}
                    onValueChange={(value) => handleConfigChange("model", value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select a model" />
                    </SelectTrigger>
                    <SelectContent>
                      {MODEL_OPTIONS.map((model) => (
                        <SelectItem key={model} value={model}>
                          {model}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Temperature */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label>Temperature</Label>
                    <span className="text-sm text-muted-foreground">
                      {editedConfig.temperature?.toFixed(2) || "0.00"}
                    </span>
                  </div>
                  <Slider
                    value={[editedConfig.temperature || 0]}
                    onValueChange={([value]: number[]) =>
                      handleConfigChange("temperature", value)
                    }
                    min={0}
                    max={2}
                    step={0.01}
                    className="w-full"
                  />
                  <p className="text-xs text-muted-foreground">
                    Controls randomness. Lower values = more focused, higher values =
                    more creative
                  </p>
                </div>

                {/* Max Tokens */}
                <div className="space-y-2">
                  <Label htmlFor="max_tokens">Max Tokens</Label>
                  <Input
                    id="max_tokens"
                    type="number"
                    value={editedConfig.max_tokens || ""}
                    onChange={(e) =>
                      handleConfigChange("max_tokens", Number.parseInt(e.target.value))
                    }
                    min={1}
                    max={8000}
                  />
                  <p className="text-xs text-muted-foreground">
                    Maximum number of tokens in the response (1-8000)
                  </p>
                </div>

                {/* Top P */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label>Top P</Label>
                    <span className="text-sm text-muted-foreground">
                      {editedConfig.top_p?.toFixed(2) || "0.00"}
                    </span>
                  </div>
                  <Slider
                    value={[editedConfig.top_p || 0]}
                    onValueChange={([value]: number[]) =>
                      handleConfigChange("top_p", value)
                    }
                    min={0}
                    max={1}
                    step={0.01}
                    className="w-full"
                  />
                  <p className="text-xs text-muted-foreground">
                    Nucleus sampling parameter. Controls diversity of token selection
                  </p>
                </div>

                {/* Timeout */}
                <div className="space-y-2">
                  <Label htmlFor="timeout_seconds">Timeout (seconds)</Label>
                  <Input
                    id="timeout_seconds"
                    type="number"
                    value={editedConfig.timeout_seconds || ""}
                    onChange={(e) =>
                      handleConfigChange(
                        "timeout_seconds",
                        Number.parseInt(e.target.value)
                      )
                    }
                    min={5}
                    max={300}
                  />
                  <p className="text-xs text-muted-foreground">
                    Request timeout in seconds (5-300)
                  </p>
                </div>

                {/* Description */}
                <div className="space-y-2">
                  <Label htmlFor="description">Description (Optional)</Label>
                  <Input
                    id="description"
                    value={editedConfig.description || ""}
                    onChange={(e) => handleConfigChange("description", e.target.value)}
                    placeholder="Describe this configuration..."
                  />
                </div>

                {hasUnsavedChanges && (
                  <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <div className="flex items-center gap-2 text-yellow-800">
                      <AlertTriangle className="h-4 w-4" />
                      <span className="text-sm font-medium">Unsaved Changes</span>
                    </div>
                    <p className="text-sm text-yellow-700 mt-1">
                      You have unsaved changes. Click "Save Changes" to apply them.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Performance Tab */}
          <TabsContent value="performance" className="space-y-4">
            {currentMetrics && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Response Time</CardTitle>
                    <Clock className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {currentMetrics.average_response_time.toFixed(0)}ms
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Average response time
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
                    <CheckCircle className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {(currentMetrics.success_rate * 100).toFixed(1)}%
                    </div>
                    <p className="text-xs text-muted-foreground">Successful requests</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Cost Estimate</CardTitle>
                    <DollarSign className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      ${currentMetrics.cost_estimate.toFixed(2)}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Estimated daily cost
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Sample Size</CardTitle>
                    <Activity className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {currentMetrics.sample_size.toLocaleString()}
                    </div>
                    <p className="text-xs text-muted-foreground">Requests analyzed</p>
                  </CardContent>
                </Card>
              </div>
            )}
          </TabsContent>

          {/* History Tab */}
          <TabsContent value="history" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <History className="h-5 w-5" />
                  Version History
                </CardTitle>
                <CardDescription>
                  View and manage configuration versions for {selectedAgent}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[400px]">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Version</TableHead>
                        <TableHead>Created</TableHead>
                        <TableHead>Created By</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {currentVersions.map((version) => (
                        <TableRow key={version.version_id}>
                          <TableCell className="font-mono text-sm">
                            {version.version_id}
                          </TableCell>
                          <TableCell>
                            {new Date(version.created_at).toLocaleString()}
                          </TableCell>
                          <TableCell>{version.created_by}</TableCell>
                          <TableCell>{version.description || "-"}</TableCell>
                          <TableCell>
                            {version.is_current && (
                              <Badge variant="default">Current</Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  // TODO: Show version details
                                  console.log("View version:", version);
                                }}
                              >
                                <Eye className="h-4 w-4" />
                              </Button>

                              {!version.is_current && (
                                <AlertDialog>
                                  <AlertDialogTrigger asChild>
                                    <Button variant="ghost" size="sm">
                                      <RotateCcw className="h-4 w-4" />
                                    </Button>
                                  </AlertDialogTrigger>
                                  <AlertDialogContent>
                                    <AlertDialogHeader>
                                      <AlertDialogTitle>
                                        Rollback Configuration
                                      </AlertDialogTitle>
                                      <AlertDialogDescription>
                                        Are you sure you want to rollback to version{" "}
                                        {version.version_id}? This will replace the
                                        current configuration and create a new version.
                                      </AlertDialogDescription>
                                    </AlertDialogHeader>
                                    <AlertDialogFooter>
                                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                                      <AlertDialogAction
                                        onClick={() =>
                                          rollbackToVersion(version.version_id)
                                        }
                                      >
                                        Rollback
                                      </AlertDialogAction>
                                    </AlertDialogFooter>
                                  </AlertDialogContent>
                                </AlertDialog>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
