import type {
  Agent,
  AgentActivity,
  AgentSession,
  AgentStatusType,
  AgentTask,
  ResourceUsage,
} from "@/types/agent-status";
import { z } from "zod";
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AgentStatusState {
  agents: Agent[];
  sessions: AgentSession[];
  currentSessionId: string | null;
  isMonitoring: boolean;
  lastUpdated: string | null;
  error: string | null;

  // Computed properties
  currentSession: AgentSession | null;
  activeAgents: Agent[];

  // Computed functions
  getCurrentSession: () => AgentSession | null;
  getActiveAgents: () => Agent[];

  // Actions
  startSession: () => void;
  endSession: (sessionId: string, status?: "completed" | "error") => void;
  addAgent: (
    agent: Omit<
      Agent,
      "id" | "createdAt" | "updatedAt" | "tasks" | "progress" | "status"
    >
  ) => void;
  updateAgentStatus: (agentId: string, status: AgentStatusType) => void;
  updateAgentProgress: (agentId: string, progress: number) => void;
  addAgentTask: (
    agentId: string,
    task: Omit<AgentTask, "id" | "createdAt" | "updatedAt" | "completedAt" | "progress">
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

// Schema for the agent status store state
const _agentStatusStoreSchema = z.object({
  agents: z.array(z.any()), // Using z.any() for now, could be made more specific
  sessions: z.array(z.any()),
  currentSessionId: z.string().nullable(),
  isMonitoring: z.boolean(),
  lastUpdated: z.string().nullable(),
  error: z.string().nullable(),
  currentSession: z.any().nullable(),
  activeAgents: z.array(z.any()),
});

export const useAgentStatusStore = create<AgentStatusState>()(
  persist(
    (set, get) => {
      const computeCurrentSession = (state: Partial<AgentStatusState>) => {
        if (!state.currentSessionId || !state.sessions) return null;
        return (
          state.sessions.find((session) => session.id === state.currentSessionId) ||
          null
        );
      };

      const computeActiveAgents = (agents: Agent[]) => {
        return agents.filter(
          (agent) =>
            agent.status !== "idle" &&
            agent.status !== "completed" &&
            agent.status !== "error"
        );
      };

      const initialState = {
        agents: [] as Agent[],
        sessions: [] as AgentSession[],
        currentSessionId: null as string | null,
        isMonitoring: false,
        lastUpdated: null as string | null,
        error: null as string | null,
      };

      return {
        ...initialState,
        currentSession: computeCurrentSession(initialState),
        activeAgents: computeActiveAgents(initialState.agents),

        getCurrentSession: () => {
          const { sessions, currentSessionId } = get();
          if (!currentSessionId) return null;
          return sessions.find((session) => session.id === currentSessionId) || null;
        },

        getActiveAgents: () => {
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

          set((state) => {
            const newState = {
              ...state,
              sessions: [newSession, ...state.sessions],
              currentSessionId: sessionId,
              isMonitoring: true,
              lastUpdated: timestamp,
            };
            return {
              ...newState,
              currentSession: computeCurrentSession(newState),
              activeAgents: computeActiveAgents(newState.agents),
            };
          });
        },

        endSession: (sessionId, status = "completed") => {
          const timestamp = getCurrentTimestamp();

          set((state) => {
            const newState = {
              ...state,
              sessions: state.sessions.map((session) =>
                session.id === sessionId
                  ? { ...session, endedAt: timestamp, status }
                  : session
              ),
              isMonitoring:
                state.currentSessionId === sessionId ? false : state.isMonitoring,
              lastUpdated: timestamp,
            };
            return {
              ...newState,
              currentSession: computeCurrentSession(newState),
              activeAgents: computeActiveAgents(newState.agents),
            };
          });
        },

        addAgent: (agentData) => {
          const { currentSessionId, sessions } = get();
          if (!currentSessionId) return;

          const currentSession = sessions.find(
            (session) => session.id === currentSessionId
          );
          if (!currentSession) return;

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

          set((state) => {
            const newState = {
              ...state,
              agents: [...state.agents, newAgent],
              sessions: state.sessions.map((session) =>
                session.id === currentSessionId
                  ? { ...session, agents: [...session.agents, newAgent] }
                  : session
              ),
              lastUpdated: timestamp,
            };
            return {
              ...newState,
              currentSession: computeCurrentSession(newState),
              activeAgents: computeActiveAgents(newState.agents),
            };
          });
        },

        updateAgentStatus: (agentId, status) => {
          const timestamp = getCurrentTimestamp();

          set((state) => {
            const newState = {
              ...state,
              agents: state.agents.map((agent) =>
                agent.id === agentId
                  ? { ...agent, status, updatedAt: timestamp }
                  : agent
              ),
              sessions: state.sessions.map((session) => ({
                ...session,
                agents: session.agents.map((agent) =>
                  agent.id === agentId
                    ? { ...agent, status, updatedAt: timestamp }
                    : agent
                ),
              })),
              lastUpdated: timestamp,
            };
            return {
              ...newState,
              currentSession: computeCurrentSession(newState),
              activeAgents: computeActiveAgents(newState.agents),
            };
          });
        },

        updateAgentProgress: (agentId, progress) => {
          const timestamp = getCurrentTimestamp();
          const clampedProgress = Math.max(0, Math.min(100, progress));

          set((state) => {
            const newState = {
              ...state,
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
            };
            return {
              ...newState,
              currentSession: computeCurrentSession(newState),
              activeAgents: computeActiveAgents(newState.agents),
            };
          });
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

          set((state) => {
            const newState = {
              ...state,
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
            };
            return {
              ...newState,
              currentSession: computeCurrentSession(newState),
              activeAgents: computeActiveAgents(newState.agents),
            };
          });
        },

        updateAgentTask: (agentId, taskId, update) => {
          const timestamp = getCurrentTimestamp();

          set((state) => {
            const newState = {
              ...state,
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
            };
            return {
              ...newState,
              currentSession: computeCurrentSession(newState),
              activeAgents: computeActiveAgents(newState.agents),
            };
          });
        },

        completeAgentTask: (agentId, taskId, error) => {
          const timestamp = getCurrentTimestamp();
          const status: "completed" | "failed" = error ? "failed" : "completed";

          set((state) => {
            const agentUpdate = (agent: Agent) => {
              if (agent.id !== agentId) return agent;

              // Find the next pending task if this was the current task
              const isCurrentTask = agent.currentTaskId === taskId;
              let nextTaskId: string | undefined = agent.currentTaskId;

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

            const newState = {
              ...state,
              agents: state.agents.map(agentUpdate),
              sessions: state.sessions.map((session) => ({
                ...session,
                agents: session.agents.map(agentUpdate),
              })),
              lastUpdated: timestamp,
            };
            return {
              ...newState,
              currentSession: computeCurrentSession(newState),
              activeAgents: computeActiveAgents(newState.agents),
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

          set((state) => {
            const newState = {
              ...state,
              sessions: state.sessions.map((session) =>
                session.id === currentSessionId
                  ? {
                      ...session,
                      activities: [...session.activities, newActivity],
                    }
                  : session
              ),
              lastUpdated: timestamp,
            };
            return {
              ...newState,
              currentSession: computeCurrentSession(newState),
              activeAgents: computeActiveAgents(newState.agents),
            };
          });
        },

        updateResourceUsage: (usageData) => {
          const { currentSessionId, currentSession } = get();
          if (!currentSessionId || !currentSession) return;

          const timestamp = getCurrentTimestamp();
          const newUsage: ResourceUsage = {
            ...usageData,
            timestamp,
          };

          set((state) => {
            const newState = {
              ...state,
              sessions: state.sessions.map((session) =>
                session.id === currentSessionId
                  ? {
                      ...session,
                      resourceUsage: [...session.resourceUsage, newUsage],
                    }
                  : session
              ),
              lastUpdated: timestamp,
            };
            return {
              ...newState,
              currentSession: computeCurrentSession(newState),
              activeAgents: computeActiveAgents(newState.agents),
            };
          });
        },

        resetAgentStatus: () => {
          const timestamp = getCurrentTimestamp();

          const newState = {
            agents: [],
            sessions: [],
            currentSessionId: null,
            isMonitoring: false,
            lastUpdated: timestamp,
            error: null,
          };

          set({
            ...newState,
            currentSession: computeCurrentSession(newState),
            activeAgents: computeActiveAgents(newState.agents),
          });
        },

        setError: (error) => {
          set((state) => {
            const newState = { ...state, error };
            return {
              ...newState,
              currentSession: computeCurrentSession(newState),
              activeAgents: computeActiveAgents(newState.agents),
            };
          });
        },
      };
    },
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
