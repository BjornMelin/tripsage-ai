import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  Agent,
  AgentActivity,
  AgentSession,
  AgentStatusType,
  AgentTask,
  ResourceUsage,
} from "@/types/agent-status";

interface AgentStatusState {
  agents: Agent[];
  sessions: AgentSession[];
  currentSessionId: string | null;
  isMonitoring: boolean;
  lastUpdated: string | null;
  error: string | null;

  // Computed
  currentSession: AgentSession | null;
  activeAgents: Agent[];

  // Actions
  startSession: () => void;
  endSession: (sessionId: string, status?: "completed" | "error") => void;
  addAgent: (
    agent: Omit<Agent, "id" | "createdAt" | "updatedAt" | "tasks" | "progress">
  ) => void;
  updateAgentStatus: (agentId: string, status: AgentStatusType) => void;
  updateAgentProgress: (agentId: string, progress: number) => void;
  addAgentTask: (
    agentId: string,
    task: Omit<AgentTask, "id" | "createdAt" | "updatedAt" | "completedAt">
  ) => void;
  updateAgentTask: (
    agentId: string,
    taskId: string,
    update: Partial<AgentTask>
  ) => void;
  completeAgentTask: (agentId: string, taskId: string, error?: string) => void;
  addAgentActivity: (activity: Omit<AgentActivity, "id" | "timestamp">) => void;
  updateResourceUsage: (usage: Omit<ResourceUsage, "timestamp">) => void;
  resetAgentStatus: () => void;
  setError: (error: string | null) => void;
}

const generateId = () =>
  Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
const getCurrentTimestamp = () => new Date().toISOString();

export const useAgentStatusStore = create<AgentStatusState>()(
  persist(
    (set, get) => ({
      agents: [],
      sessions: [],
      currentSessionId: null,
      isMonitoring: false,
      lastUpdated: null,
      error: null,

      get currentSession() {
        const { sessions, currentSessionId } = get();
        if (!currentSessionId) return null;
        return sessions.find((session) => session.id === currentSessionId) || null;
      },

      get activeAgents() {
        return get().agents.filter(
          (agent) =>
            agent.status !== "idle" &&
            agent.status !== "completed" &&
            agent.status !== "error"
        );
      },

      startSession: () => {
        const sessionId = generateId();
        const timestamp = getCurrentTimestamp();

        const newSession: AgentSession = {
          id: sessionId,
          agents: [],
          activities: [],
          resourceUsage: [],
          startedAt: timestamp,
          status: "active",
        };

        set((state) => ({
          sessions: [newSession, ...state.sessions],
          currentSessionId: sessionId,
          isMonitoring: true,
          lastUpdated: timestamp,
        }));
      },

      endSession: (sessionId, status = "completed") => {
        const timestamp = getCurrentTimestamp();

        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? { ...session, endedAt: timestamp, status }
              : session
          ),
          isMonitoring:
            state.currentSessionId === sessionId ? false : state.isMonitoring,
          lastUpdated: timestamp,
        }));
      },

      addAgent: (agentData) => {
        const { currentSessionId, currentSession } = get();
        if (!currentSessionId || !currentSession) return;

        const timestamp = getCurrentTimestamp();
        const newAgent: Agent = {
          id: generateId(),
          ...agentData,
          status: "initializing",
          progress: 0,
          tasks: [],
          createdAt: timestamp,
          updatedAt: timestamp,
        };

        set((state) => ({
          agents: [...state.agents, newAgent],
          sessions: state.sessions.map((session) =>
            session.id === currentSessionId
              ? { ...session, agents: [...session.agents, newAgent] }
              : session
          ),
          lastUpdated: timestamp,
        }));
      },

      updateAgentStatus: (agentId, status) => {
        const timestamp = getCurrentTimestamp();

        set((state) => ({
          agents: state.agents.map((agent) =>
            agent.id === agentId ? { ...agent, status, updatedAt: timestamp } : agent
          ),
          sessions: state.sessions.map((session) => ({
            ...session,
            agents: session.agents.map((agent) =>
              agent.id === agentId ? { ...agent, status, updatedAt: timestamp } : agent
            ),
          })),
          lastUpdated: timestamp,
        }));
      },

      updateAgentProgress: (agentId, progress) => {
        const timestamp = getCurrentTimestamp();
        const clampedProgress = Math.max(0, Math.min(100, progress));

        set((state) => ({
          agents: state.agents.map((agent) =>
            agent.id === agentId
              ? { ...agent, progress: clampedProgress, updatedAt: timestamp }
              : agent
          ),
          sessions: state.sessions.map((session) => ({
            ...session,
            agents: session.agents.map((agent) =>
              agent.id === agentId
                ? { ...agent, progress: clampedProgress, updatedAt: timestamp }
                : agent
            ),
          })),
          lastUpdated: timestamp,
        }));
      },

      addAgentTask: (agentId, taskData) => {
        const timestamp = getCurrentTimestamp();
        const newTask: AgentTask = {
          id: generateId(),
          ...taskData,
          createdAt: timestamp,
          updatedAt: timestamp,
        };

        // Update agent's current task if it doesn't have one and task status is in_progress
        const updateCurrentTask = taskData.status === "in_progress";

        set((state) => ({
          agents: state.agents.map((agent) =>
            agent.id === agentId
              ? {
                  ...agent,
                  tasks: [...agent.tasks, newTask],
                  currentTaskId:
                    updateCurrentTask && !agent.currentTaskId
                      ? newTask.id
                      : agent.currentTaskId,
                  updatedAt: timestamp,
                }
              : agent
          ),
          sessions: state.sessions.map((session) => ({
            ...session,
            agents: session.agents.map((agent) =>
              agent.id === agentId
                ? {
                    ...agent,
                    tasks: [...agent.tasks, newTask],
                    currentTaskId:
                      updateCurrentTask && !agent.currentTaskId
                        ? newTask.id
                        : agent.currentTaskId,
                    updatedAt: timestamp,
                  }
                : agent
            ),
          })),
          lastUpdated: timestamp,
        }));
      },

      updateAgentTask: (agentId, taskId, update) => {
        const timestamp = getCurrentTimestamp();

        set((state) => ({
          agents: state.agents.map((agent) =>
            agent.id === agentId
              ? {
                  ...agent,
                  tasks: agent.tasks.map((task) =>
                    task.id === taskId
                      ? { ...task, ...update, updatedAt: timestamp }
                      : task
                  ),
                  updatedAt: timestamp,
                }
              : agent
          ),
          sessions: state.sessions.map((session) => ({
            ...session,
            agents: session.agents.map((agent) =>
              agent.id === agentId
                ? {
                    ...agent,
                    tasks: agent.tasks.map((task) =>
                      task.id === taskId
                        ? { ...task, ...update, updatedAt: timestamp }
                        : task
                    ),
                    updatedAt: timestamp,
                  }
                : agent
            ),
          })),
          lastUpdated: timestamp,
        }));
      },

      completeAgentTask: (agentId, taskId, error) => {
        const timestamp = getCurrentTimestamp();
        const status = error ? "failed" : "completed";

        set((state) => {
          const agentUpdate = (agent: Agent) => {
            if (agent.id !== agentId) return agent;

            // Find the next pending task if this was the current task
            const isCurrentTask = agent.currentTaskId === taskId;
            let nextTaskId = agent.currentTaskId;

            if (isCurrentTask) {
              const pendingTask = agent.tasks.find((t) => t.status === "pending");
              nextTaskId = pendingTask?.id;
            }

            return {
              ...agent,
              tasks: agent.tasks.map((task) =>
                task.id === taskId
                  ? {
                      ...task,
                      status,
                      completedAt: timestamp,
                      error,
                      updatedAt: timestamp,
                    }
                  : task
              ),
              currentTaskId: nextTaskId,
              updatedAt: timestamp,
            };
          };

          return {
            agents: state.agents.map(agentUpdate),
            sessions: state.sessions.map((session) => ({
              ...session,
              agents: session.agents.map(agentUpdate),
            })),
            lastUpdated: timestamp,
          };
        });
      },

      addAgentActivity: (activityData) => {
        const { currentSessionId, currentSession } = get();
        if (!currentSessionId || !currentSession) return;

        const timestamp = getCurrentTimestamp();
        const newActivity: AgentActivity = {
          id: generateId(),
          ...activityData,
          timestamp,
        };

        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === currentSessionId
              ? {
                  ...session,
                  activities: [...session.activities, newActivity],
                }
              : session
          ),
          lastUpdated: timestamp,
        }));
      },

      updateResourceUsage: (usageData) => {
        const { currentSessionId, currentSession } = get();
        if (!currentSessionId || !currentSession) return;

        const timestamp = getCurrentTimestamp();
        const newUsage: ResourceUsage = {
          ...usageData,
          timestamp,
        };

        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === currentSessionId
              ? {
                  ...session,
                  resourceUsage: [...session.resourceUsage, newUsage],
                }
              : session
          ),
          lastUpdated: timestamp,
        }));
      },

      resetAgentStatus: () => {
        const timestamp = getCurrentTimestamp();

        set({
          agents: [],
          currentSessionId: null,
          isMonitoring: false,
          lastUpdated: timestamp,
          error: null,
        });
      },

      setError: (error) => set({ error }),
    }),
    {
      name: "agent-status-storage",
      partialize: (state) => ({
        sessions: state.sessions.map((session) => ({
          ...session,
          // Truncate long activity lists to keep storage size reasonable
          activities: session.activities.slice(-100),
          resourceUsage: session.resourceUsage.slice(-50),
        })),
        currentSessionId: state.currentSessionId,
      }),
    }
  )
);
