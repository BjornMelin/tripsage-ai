/**
 * @fileoverview Admin UI for managing agent configuration with version history.
 * Uses server actions for data access; no client-side fetching side effects.
 */

"use client";

import type { AgentConfig, AgentType } from "@schemas/configuration";
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  History,
  RotateCcw,
  Save,
  Settings,
} from "lucide-react";
import { useState, useTransition } from "react";
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
import {
  type AgentMetrics,
  type AgentVersion,
  fetchAgentBundle,
  rollbackAgentConfigAction,
  updateAgentConfigAction,
} from "./configuration-actions";

const AGENTS: Array<{ label: string; value: AgentType; description: string }> = [
  { description: "Budget optimization", label: "Budget Agent", value: "budgetAgent" },
  {
    description: "Research destinations and attractions",
    label: "Destination Research Agent",
    value: "destinationResearchAgent",
  },
  {
    description: "Plan itineraries",
    label: "Itinerary Agent",
    value: "itineraryAgent",
  },
  { description: "Search flights", label: "Flight Agent", value: "flightAgent" },
  {
    description: "Find stays",
    label: "Accommodation Agent",
    value: "accommodationAgent",
  },
  { description: "Persist memories", label: "Memory Agent", value: "memoryAgent" },
];

export type ConfigurationManagerProps = {
  initialAgent: AgentType;
  initialConfig: AgentConfig;
  initialVersions: AgentVersion[];
  initialMetrics: AgentMetrics;
};

export default function ConfigurationManager(props: ConfigurationManagerProps) {
  const { toast } = useToast();
  const [selectedAgent, setSelectedAgent] = useState<AgentType>(props.initialAgent);
  const [config, setConfig] = useState<AgentConfig>(props.initialConfig);
  const [edited, setEdited] = useState<Partial<AgentConfig["parameters"]>>({
    ...props.initialConfig.parameters,
  });
  const [versions, setVersions] = useState<AgentVersion[]>(props.initialVersions);
  const [metrics, setMetrics] = useState<AgentMetrics>(props.initialMetrics);
  const [saving, startSaving] = useTransition();
  const [loading, startLoading] = useTransition();
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const applyAgentData = (bundle: Awaited<ReturnType<typeof fetchAgentBundle>>) => {
    setConfig(bundle.config);
    setEdited({ ...bundle.config.parameters });
    setVersions(bundle.versions);
    setMetrics(bundle.metrics);
    setHasUnsavedChanges(false);
  };

  const handleAgentChange = (value: AgentType) => {
    startLoading(async () => {
      try {
        const bundle = await fetchAgentBundle(value);
        setSelectedAgent(value);
        applyAgentData(bundle);
      } catch (error) {
        toast({
          description: error instanceof Error ? error.message : "Failed to load agent",
          title: "Load failed",
          variant: "destructive",
        });
      }
    });
  };

  const handleSave = () => {
    startSaving(async () => {
      try {
        const payload = {
          ...edited,
        };
        const res = await updateAgentConfigAction(selectedAgent, payload);
        const bundle = await fetchAgentBundle(selectedAgent);
        applyAgentData(bundle);
        toast({
          description: `Saved configuration (version ${res.versionId})`,
          title: "Configuration saved",
        });
      } catch (error) {
        toast({
          description: error instanceof Error ? error.message : "Failed to save",
          title: "Save failed",
          variant: "destructive",
        });
      }
    });
  };

  const handleRollback = (versionId: string) => {
    startSaving(async () => {
      try {
        await rollbackAgentConfigAction(selectedAgent, versionId);
        const bundle = await fetchAgentBundle(selectedAgent);
        applyAgentData(bundle);
        toast({
          description: `Rolled back to version ${versionId}`,
          title: "Rollback successful",
        });
      } catch (error) {
        toast({
          description: error instanceof Error ? error.message : "Failed to rollback",
          title: "Rollback failed",
          variant: "destructive",
        });
      }
    });
  };

  const onParamChange = (
    field: keyof AgentConfig["parameters"],
    value: number | string | null
  ) => {
    setEdited((prev) => ({ ...prev, [field]: value ?? undefined }));
    setHasUnsavedChanges(true);
  };

  const currentParams = { ...config.parameters, ...edited };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Agent Configuration</h1>
          <p className="text-muted-foreground">
            Manage parameters, history, and rollbacks
          </p>
        </div>
        {loading && <LoadingSpinner size="sm" />}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Select Agent
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Select
            value={selectedAgent}
            onValueChange={(v) => handleAgentChange(v as AgentType)}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select an agent" />
            </SelectTrigger>
            <SelectContent>
              {AGENTS.map((agent) => (
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

      <Tabs defaultValue="configuration" className="space-y-4">
        <TabsList>
          <TabsTrigger value="configuration">Configuration</TabsTrigger>
          <TabsTrigger value="performance">Metrics</TabsTrigger>
          <TabsTrigger value="history">Version History</TabsTrigger>
        </TabsList>

        <TabsContent value="configuration" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Agent Parameters</CardTitle>
                <CardDescription>Configured scope: global</CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setEdited({ ...config.parameters });
                    setHasUnsavedChanges(false);
                  }}
                  disabled={!hasUnsavedChanges || saving}
                >
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Reset
                </Button>
                <Button onClick={handleSave} disabled={!hasUnsavedChanges || saving}>
                  {saving ? (
                    <LoadingSpinner size="sm" className="mr-2" />
                  ) : (
                    <Save className="h-4 w-4 mr-2" />
                  )}
                  Save Changes
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="model">Model</Label>
                <Input
                  id="model"
                  value={currentParams.model ?? ""}
                  onChange={(e) => onParamChange("model", e.target.value)}
                  placeholder="gpt-4o"
                />
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Temperature</Label>
                  <span className="text-sm text-muted-foreground">
                    {typeof currentParams.temperature === "number"
                      ? currentParams.temperature.toFixed(2)
                      : "0.00"}
                  </span>
                </div>
                <Slider
                  value={[currentParams.temperature ?? 0]}
                  onValueChange={([v]) => onParamChange("temperature", v)}
                  min={0}
                  max={2}
                  step={0.01}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="maxTokens">Max Tokens</Label>
                <Input
                  id="maxTokens"
                  type="number"
                  value={currentParams.maxTokens ?? ""}
                  onChange={(e) =>
                    onParamChange("maxTokens", Number.parseInt(e.target.value, 10))
                  }
                  min={1}
                  max={8000}
                />
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Top P</Label>
                  <span className="text-sm text-muted-foreground">
                    {typeof currentParams.topP === "number"
                      ? currentParams.topP.toFixed(2)
                      : "0.00"}
                  </span>
                </div>
                <Slider
                  value={[currentParams.topP ?? 0]}
                  onValueChange={([v]) => onParamChange("topP", v)}
                  min={0}
                  max={1}
                  step={0.01}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="timeoutSeconds">Timeout (seconds)</Label>
                <Input
                  id="timeoutSeconds"
                  type="number"
                  value={currentParams.timeoutSeconds ?? ""}
                  onChange={(e) =>
                    onParamChange("timeoutSeconds", Number.parseInt(e.target.value, 10))
                  }
                  min={5}
                  max={300}
                />
              </div>

              {hasUnsavedChanges && (
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <div className="flex items-center gap-2 text-yellow-800">
                    <AlertTriangle className="h-4 w-4" />
                    <span className="text-sm font-medium">Unsaved Changes</span>
                  </div>
                  <p className="text-sm text-yellow-700 mt-1">
                    Save changes to update the active configuration and create a
                    version.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Versions</CardTitle>
                <History className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{metrics.versionCount}</div>
                <p className="text-xs text-muted-foreground">Total versions stored</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Last Updated</CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metrics.lastUpdatedAt
                    ? new Date(metrics.lastUpdatedAt).toLocaleString()
                    : "—"}
                </div>
                <p className="text-xs text-muted-foreground">
                  Latest configuration change
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Config Health</CardTitle>
                <CheckCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">OK</div>
                <p className="text-xs text-muted-foreground">Schema validated</p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="h-5 w-5" />
                Version History
              </CardTitle>
              <CardDescription>Recent versions for {selectedAgent}</CardDescription>
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
                    {versions.map((version, index) => (
                      <TableRow key={version.id}>
                        <TableCell className="font-mono text-sm">
                          {version.id}
                        </TableCell>
                        <TableCell>
                          {new Date(version.createdAt).toLocaleString()}
                        </TableCell>
                        <TableCell>{version.createdBy ?? "—"}</TableCell>
                        <TableCell>{version.summary ?? "-"}</TableCell>
                        <TableCell>
                          {index === 0 && <Badge variant="default">Current</Badge>}
                        </TableCell>
                        <TableCell>
                          {index !== 0 && (
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
                                    Roll back to version {version.id}? A new head
                                    version will be created.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                                  <AlertDialogAction
                                    onClick={() => handleRollback(version.id)}
                                  >
                                    Rollback
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          )}
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
    </div>
  );
}
