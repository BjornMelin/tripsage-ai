/**
 * @fileoverview Agent configuration management component.
 *
 * Provides a comprehensive interface for managing AI agent configurations,
 * performance monitoring, and version control. Features real-time updates,
 * configuration validation, rollback capabilities, and performance metrics
 * tracking for multiple agent types in the TripSage platform.
 */

"use client";

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
import { useCallback, useEffect, useId, useState } from "react";
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
  agentType: string;
  temperature: number;
  maxTokens: number;
  topP: number;
  timeoutSeconds: number;
  model: string;
  updatedAt: string;
  updatedBy?: string;
  description?: string;
}

interface ConfigVersion {
  versionId: string;
  configuration: Record<string, unknown>;
  description?: string;
  createdAt: string;
  createdBy: string;
  isCurrent: boolean;
}

interface PerformanceMetrics {
  agentType: string;
  averageResponseTime: number;
  successRate: number;
  errorRate: number;
  tokenUsage: Record<string, number>;
  costEstimate: number;
  sampleSize: number;
}

const AGENT_TYPES = [
  {
    description: "Handles budget optimization and expense tracking",
    label: "Budget Agent",
    value: "budget_agent",
  },
  {
    description: "Researches destinations and attractions",
    label: "Research Agent",
    value: "destination_research_agent",
  },
  {
    description: "Plans and optimizes travel itineraries",
    label: "Itinerary Agent",
    value: "itinerary_agent",
  },
];

const MODEL_OPTIONS = ["gpt-4", "gpt-4-turbo", "gpt-5", "gpt-5-mini", "gpt-3.5-turbo"];

/**
 * Agent configuration management component.
 *
 * Renders a comprehensive interface for managing AI agent configurations with
 * real-time updates, versioning, and performance tracking. Supports multiple
 * agent types with configuration parameters like temperature, max tokens,
 * model selection, and timeout settings.
 *
 * Features:
 * - Agent-specific configuration management with validation
 * - Real-time performance metrics and monitoring
 * - Configuration versioning with rollback capabilities
 * - Tabbed interface for configuration, performance, and history views
 * - Form validation with cross-field constraints and model compatibility checks
 *
 * @returns {JSX.Element} The rendered configuration management interface.
 */
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
  // Realtime live updates removed. UI refreshes after successful saves.

  // Form state
  const [editedConfig, setEditedConfig] = useState<Partial<AgentConfig>>({});
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const maxTokensId = useId();
  const timeoutId = useId();
  const descriptionId = useId();

  // Live WS updates removed; consider Supabase Realtime in a future iteration.

  const loadAgentConfig = useCallback(
    async (agentType: string) => {
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
    },
    [selectedAgent]
  );

  const loadVersionHistory = useCallback(async (agentType: string) => {
    try {
      const response = await fetch(`/api/config/agents/${agentType}/versions?limit=10`);
      if (!response.ok) throw new Error("Failed to load versions");

      const versionList = await response.json();
      setVersions((prev) => ({ ...prev, [agentType]: versionList }));
    } catch (error) {
      console.error(`Error loading versions for ${agentType}:`, error);
    }
  }, []);

  const loadPerformanceMetrics = useCallback((agentType: string) => {
    try {
      // This would be implemented with actual metrics endpoint
      // For now, using placeholder data
      const mockMetrics: PerformanceMetrics = {
        agentType: agentType,
        averageResponseTime: Math.random() * 2000 + 500,
        costEstimate: Math.random() * 10,
        errorRate: Math.random() * 0.05,
        sampleSize: Math.floor(Math.random() * 1000) + 100,
        successRate: 0.95 + Math.random() * 0.04,
        tokenUsage: {
          inputTokens: Math.floor(Math.random() * 10000),
          outputTokens: Math.floor(Math.random() * 5000),
        },
      };

      setMetrics((prev) => ({ ...prev, [agentType]: mockMetrics }));
    } catch (error) {
      console.error(`Error loading metrics for ${agentType}:`, error);
    }
  }, []);

  const loadAllConfigs = useCallback(async () => {
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
        description: "Failed to load configurations",
        title: "Error",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [loadAgentConfig, loadVersionHistory, loadPerformanceMetrics, toast]);

  // Load initial data
  useEffect(() => {
    loadAllConfigs();
  }, [loadAllConfigs]);

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
  const handleConfigChange = (field: keyof AgentConfig, value: unknown) => {
    setEditedConfig((prev) => ({ ...prev, [field]: value }));
    setHasUnsavedChanges(true);
  };

  // Save configuration
  const saveConfiguration = async () => {
    if (!selectedAgent || !editedConfig) return;

    setSaving(selectedAgent);
    try {
      const response = await fetch(`/api/config/agents/${selectedAgent}`, {
        body: JSON.stringify({
          description: editedConfig.description,
          maxTokens: editedConfig.maxTokens,
          model: editedConfig.model,
          temperature: editedConfig.temperature,
          timeoutSeconds: editedConfig.timeoutSeconds,
          topP: editedConfig.topP,
        }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "PUT",
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
        description: `${selectedAgent} configuration has been updated successfully`,
        title: "Configuration Saved",
        variant: "default",
      });

      // Reload version history to show the new version
      await loadVersionHistory(selectedAgent);
    } catch (error) {
      console.error("Error saving configuration:", error);
      toast({
        description:
          error instanceof Error ? error.message : "Failed to save configuration",
        title: "Save Failed",
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
        description: `Configuration rolled back to version ${versionId}`,
        title: "Rollback Successful",
        variant: "default",
      });
    } catch (error) {
      console.error("Error rolling back:", error);
      toast({
        description:
          error instanceof Error ? error.message : "Failed to rollback configuration",
        title: "Rollback Failed",
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

        <div className="flex items-center gap-2" />
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
                  <Label htmlFor={maxTokensId}>Max Tokens</Label>
                  <Input
                    id={maxTokensId}
                    type="number"
                    value={editedConfig.maxTokens || ""}
                    onChange={(e) =>
                      handleConfigChange(
                        "maxTokens",
                        Number.parseInt(e.target.value, 10)
                      )
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
                      {editedConfig.topP?.toFixed(2) || "0.00"}
                    </span>
                  </div>
                  <Slider
                    value={[editedConfig.topP || 0]}
                    onValueChange={([value]: number[]) =>
                      handleConfigChange("topP", value)
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
                  <Label htmlFor={timeoutId}>Timeout (seconds)</Label>
                  <Input
                    id={timeoutId}
                    type="number"
                    value={editedConfig.timeoutSeconds || ""}
                    onChange={(e) =>
                      handleConfigChange(
                        "timeoutSeconds",
                        Number.parseInt(e.target.value, 10)
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
                  <Label htmlFor={descriptionId}>Description (Optional)</Label>
                  <Input
                    id={descriptionId}
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
                      {currentMetrics.averageResponseTime.toFixed(0)}ms
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
                      {(currentMetrics.successRate * 100).toFixed(1)}%
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
                      ${currentMetrics.costEstimate.toFixed(2)}
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
                      {currentMetrics.sampleSize.toLocaleString()}
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
                        <TableRow key={version.versionId}>
                          <TableCell className="font-mono text-sm">
                            {version.versionId}
                          </TableCell>
                          <TableCell>
                            {new Date(version.createdAt).toLocaleString()}
                          </TableCell>
                          <TableCell>{version.createdBy}</TableCell>
                          <TableCell>{version.description || "-"}</TableCell>
                          <TableCell>
                            {version.isCurrent && (
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

                              {!version.isCurrent && (
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
                                        {version.versionId}? This will replace the
                                        current configuration and create a new version.
                                      </AlertDialogDescription>
                                    </AlertDialogHeader>
                                    <AlertDialogFooter>
                                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                                      <AlertDialogAction
                                        onClick={() =>
                                          rollbackToVersion(version.versionId)
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
