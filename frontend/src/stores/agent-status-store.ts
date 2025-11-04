/**
 * @fileoverview Zustand store for agent status state and actions.
 */

// import { z } from "zod"; // Future validation
import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  Agent,
  AgentActivity,
  AgentSession,
  AgentStatusType,
  AgentTask,
  ResourceUsage,
} from "@/lib/schemas/agent-status";
import { nowIso, secureId } from "@/lib/security/random";

/**
 * Interface for the agent status state.
 */
export interface AgentStatusState {
  // Agent status state
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

const GENERATE_ID = () => secureId(12);
const GET_CURRENT_TIMESTAMP = () => nowIso();

// Schema for the agent status store state
// const agentStatusStoreSchema = z.object({ // Future validation
//   agents: z.array(z.any()), // Using z.any() for now, could be made more specific
//   sessions: z.array(z.any()),
//   currentSessionId: z.string().nullable(),
//   isMonitoring: z.boolean(),
//   lastUpdated: z.string().nullable(),
//   error: z.string().nullable(),
//   currentSession: z.any().nullable(),
//   activeAgents: z.array(z.any()),
// });

/**
 * Zustand store for the agent status state and actions.
 *
 * @returns The agent status store.
 */
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

      /**
       * Compute the active agents.
       *
       * @param agents - The agents to compute the active agents from.
       * @returns The active agents.
       */
      const computeActiveAgents = (agents: Agent[]) => {
        return agents.filter(
          (agent) =>
            agent.status !== "idle" &&
            agent.status !== "completed" &&
            agent.status !== "error"
        );
      };

      /**
       * Initial state for the agent status store.
       *
       * @returns The initial state.
       */
      const initialState = {
        agents: [] as Agent[],
        currentSessionId: null as string | null,
        error: null as string | null,
        isMonitoring: false,
        lastUpdated: null as string | null,
        sessions: [] as AgentSession[],
      };

      return {
        ...initialState,
        activeAgents: computeActiveAgents(initialState.agents),

        // Add an agent to the session.
        addAgent: (agentData) => {
          const { currentSessionId, sessions } = get();
          if (!currentSessionId) return;

          const currentSession = sessions.find(
            (session) => session.id === currentSessionId
          );
          if (!currentSession) return;

          const timestamp = GET_CURRENT_TIMESTAMP();
          const newAgent: Agent = {
            id: GENERATE_ID(),
            ...agentData,
            createdAt: timestamp,
            progress: 0,
            status: "initializing",
            tasks: [],
            updatedAt: timestamp,
          };

          set((state) => {
            const newState = {
              ...state,
              agents: [...state.agents, newAgent],
              lastUpdated: timestamp,
              sessions: state.sessions.map((session) =>
                session.id === currentSessionId
                  ? { ...session, agents: [...session.agents, newAgent] }
                  : session
              ),
            };
            return {
              ...newState,
              activeAgents: computeActiveAgents(newState.agents),
              currentSession: computeCurrentSession(newState),
            };
          });
        },

        // Add an activity to the session.
        addAgentActivity: (activityData) => {
          const { currentSessionId, currentSession } = get();
          if (!currentSessionId || !currentSession) return;

          const timestamp = GET_CURRENT_TIMESTAMP();
          const newActivity: AgentActivity = {
            id: GENERATE_ID(),
            ...activityData,
            timestamp,
          };

          set((state) => {
            const newState = {
              ...state,
              lastUpdated: timestamp,
              sessions: state.sessions.map((session) =>
                session.id === currentSessionId
                  ? {
                      ...session,
                      activities: [...session.activities, newActivity],
                    }
                  : session
              ),
            };
            return {
              ...newState,
              activeAgents: computeActiveAgents(newState.agents),
              currentSession: computeCurrentSession(newState),
            };
          });
        },

        // Add a task to the agent.
        addAgentTask: (agentId, taskData) => {
          const timestamp = GET_CURRENT_TIMESTAMP();
          const newTask: AgentTask = {
            id: GENERATE_ID(),
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
                      currentTaskId:
                        updateCurrentTask && !agent.currentTaskId
                          ? newTask.id
                          : agent.currentTaskId,
                      tasks: [...agent.tasks, newTask],
                      updatedAt: timestamp,
                    }
                  : agent
              ),
              lastUpdated: timestamp,
              sessions: state.sessions.map((session) => ({
                ...session,
                agents: session.agents.map((agent) =>
                  agent.id === agentId
                    ? {
                        ...agent,
                        currentTaskId:
                          updateCurrentTask && !agent.currentTaskId
                            ? newTask.id
                            : agent.currentTaskId,
                        tasks: [...agent.tasks, newTask],
                        updatedAt: timestamp,
                      }
                    : agent
                ),
              })),
            };
            return {
              ...newState,
              activeAgents: computeActiveAgents(newState.agents),
              currentSession: computeCurrentSession(newState),
            };
          });
        },

        // Complete a task for an agent.
        completeAgentTask: (agentId, taskId, error) => {
          const timestamp = GET_CURRENT_TIMESTAMP();
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
                currentTaskId: nextTaskId,
                tasks: agent.tasks.map((task) =>
                  task.id === taskId
                    ? {
                        ...task,
                        completedAt: timestamp,
                        error,
                        status,
                        updatedAt: timestamp,
                      }
                    : task
                ),
                updatedAt: timestamp,
              };
            };

            const newState = {
              ...state,
              agents: state.agents.map(agentUpdate),
              lastUpdated: timestamp,
              sessions: state.sessions.map((session) => ({
                ...session,
                agents: session.agents.map(agentUpdate),
              })),
            };
            return {
              ...newState,
              activeAgents: computeActiveAgents(newState.agents),
              currentSession: computeCurrentSession(newState),
            };
          });
        },

        // The current session.
        currentSession: computeCurrentSession(initialState),

        // End a session.
        endSession: (sessionId, status = "completed") => {
          const timestamp = GET_CURRENT_TIMESTAMP();

          set((state) => {
            const newState = {
              ...state,
              isMonitoring:
                state.currentSessionId === sessionId ? false : state.isMonitoring,
              lastUpdated: timestamp,
              sessions: state.sessions.map((session) =>
                session.id === sessionId
                  ? { ...session, endedAt: timestamp, status }
                  : session
              ),
            };
            return {
              ...newState,
              activeAgents: computeActiveAgents(newState.agents),
              currentSession: computeCurrentSession(newState),
            };
          });
        },

        // Get the active agents.
        getActiveAgents: () => {
          return get().agents.filter(
            (agent) =>
              agent.status !== "idle" &&
              agent.status !== "completed" &&
              agent.status !== "error"
          );
        },

        // Get the current session.
        getCurrentSession: () => {
          const { sessions, currentSessionId } = get();
          if (!currentSessionId) return null;
          return sessions.find((session) => session.id === currentSessionId) || null;
        },

        // Reset the agent status.
        resetAgentStatus: () => {
          const timestamp = GET_CURRENT_TIMESTAMP();

          const newState = {
            agents: [],
            currentSessionId: null,
            error: null,
            isMonitoring: false,
            lastUpdated: timestamp,
            sessions: [],
          };

          set({
            ...newState,
            activeAgents: computeActiveAgents(newState.agents),
            currentSession: computeCurrentSession(newState),
          });
        },

        // Set an error.
        setError: (error) => {
          set((state) => {
            const newState = { ...state, error };
            return {
              ...newState,
              activeAgents: computeActiveAgents(newState.agents),
              currentSession: computeCurrentSession(newState),
            };
          });
        },

        // Start a new session.
        startSession: () => {
          const sessionId = GENERATE_ID();
          const timestamp = GET_CURRENT_TIMESTAMP();

          const newSession: AgentSession = {
            activities: [],
            agents: [],
            id: sessionId,
            resourceUsage: [],
            startedAt: timestamp,
            status: "active",
          };

          set((state) => {
            const newState = {
              ...state,
              currentSessionId: sessionId,
              isMonitoring: true,
              lastUpdated: timestamp,
              sessions: [newSession, ...state.sessions],
            };
            return {
              ...newState,
              activeAgents: computeActiveAgents(newState.agents),
              currentSession: computeCurrentSession(newState),
            };
          });
        },

        // Update the progress of an agent.
        updateAgentProgress: (agentId, progress) => {
          const timestamp = GET_CURRENT_TIMESTAMP();
          const clampedProgress = Math.max(0, Math.min(100, progress));

          set((state) => {
            const newState = {
              ...state,
              agents: state.agents.map((agent) =>
                agent.id === agentId
                  ? { ...agent, progress: clampedProgress, updatedAt: timestamp }
                  : agent
              ),
              lastUpdated: timestamp,
              sessions: state.sessions.map((session) => ({
                ...session,
                agents: session.agents.map((agent) =>
                  agent.id === agentId
                    ? { ...agent, progress: clampedProgress, updatedAt: timestamp }
                    : agent
                ),
              })),
            };
            return {
              ...newState,
              activeAgents: computeActiveAgents(newState.agents),
              currentSession: computeCurrentSession(newState),
            };
          });
        },

        // Update the status of an agent.
        updateAgentStatus: (agentId, status) => {
          const timestamp = GET_CURRENT_TIMESTAMP();

          set((state) => {
            const newState = {
              ...state,
              agents: state.agents.map((agent) =>
                agent.id === agentId
                  ? { ...agent, status, updatedAt: timestamp }
                  : agent
              ),
              lastUpdated: timestamp,
              sessions: state.sessions.map((session) => ({
                ...session,
                agents: session.agents.map((agent) =>
                  agent.id === agentId
                    ? { ...agent, status, updatedAt: timestamp }
                    : agent
                ),
              })),
            };
            return {
              ...newState,
              activeAgents: computeActiveAgents(newState.agents),
              currentSession: computeCurrentSession(newState),
            };
          });
        },

        // Update a task for an agent.
        updateAgentTask: (agentId, taskId, update) => {
          const timestamp = GET_CURRENT_TIMESTAMP();

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
              lastUpdated: timestamp,
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
            };
            return {
              ...newState,
              activeAgents: computeActiveAgents(newState.agents),
              currentSession: computeCurrentSession(newState),
            };
          });
        },

        // Update the resource usage for a session.
        updateResourceUsage: (usageData) => {
          const { currentSessionId, currentSession } = get();
          if (!currentSessionId || !currentSession) return;

          const timestamp = GET_CURRENT_TIMESTAMP();
          const newUsage: ResourceUsage = {
            ...usageData,
            timestamp,
          };

          set((state) => {
            const newState = {
              ...state,
              lastUpdated: timestamp,
              sessions: state.sessions.map((session) =>
                session.id === currentSessionId
                  ? {
                      ...session,
                      resourceUsage: [...session.resourceUsage, newUsage],
                    }
                  : session
              ),
            };
            return {
              ...newState,
              activeAgents: computeActiveAgents(newState.agents),
              currentSession: computeCurrentSession(newState),
            };
          });
        },
      };
    },
    {
      name: "agent-status-storage",
      partialize: (state) => ({
        currentSessionId: state.currentSessionId,
        sessions: state.sessions.map((session) => ({
          ...session,
          // Truncate long activity lists to keep storage size reasonable
          activities: session.activities.slice(-100),
          resourceUsage: session.resourceUsage.slice(-50),
        })),
      }),
    }
  )
);
