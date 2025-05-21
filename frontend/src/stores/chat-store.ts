import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
}

interface ChatState {
  sessions: ChatSession[];
  currentSessionId: string | null;
  isLoading: boolean;
  error: string | null;
  
  // Computed
  currentSession: ChatSession | null;
  
  // Actions
  createSession: (title?: string) => void;
  setCurrentSession: (sessionId: string) => void;
  deleteSession: (sessionId: string) => void;
  renameSession: (sessionId: string, title: string) => void;
  addMessage: (sessionId: string, message: Omit<Message, "id" | "timestamp">) => void;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: (sessionId: string) => void;
  clearError: () => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      sessions: [],
      currentSessionId: null,
      isLoading: false,
      error: null,
      
      get currentSession() {
        const { sessions, currentSessionId } = get();
        if (!currentSessionId) return null;
        return sessions.find((session) => session.id === currentSessionId) || null;
      },
      
      createSession: (title) => {
        const timestamp = new Date().toISOString();
        const newSession: ChatSession = {
          id: Date.now().toString(),
          title: title || "New Conversation",
          messages: [],
          createdAt: timestamp,
          updatedAt: timestamp,
        };
        
        set((state) => ({
          sessions: [newSession, ...state.sessions],
          currentSessionId: newSession.id,
        }));
      },
      
      setCurrentSession: (sessionId) => {
        set({ currentSessionId: sessionId });
      },
      
      deleteSession: (sessionId) => {
        set((state) => {
          const sessions = state.sessions.filter((session) => session.id !== sessionId);
          
          // If we're deleting the current session, select the first available or null
          const currentSessionId = state.currentSessionId === sessionId
            ? sessions.length > 0 ? sessions[0].id : null
            : state.currentSessionId;
          
          return { sessions, currentSessionId };
        });
      },
      
      renameSession: (sessionId, title) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId 
              ? { ...session, title, updatedAt: new Date().toISOString() }
              : session
          ),
        }));
      },
      
      addMessage: (sessionId, message) => {
        const timestamp = new Date().toISOString();
        const newMessage: Message = {
          id: Date.now().toString(),
          ...message,
          timestamp,
        };
        
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  messages: [...session.messages, newMessage],
                  updatedAt: timestamp,
                }
              : session
          ),
        }));
      },
      
      sendMessage: async (content) => {
        const { currentSessionId, currentSession } = get();
        
        // Create a new session if none exists
        if (!currentSessionId || !currentSession) {
          get().createSession("New Conversation");
        }
        
        const sessionId = get().currentSessionId!;
        
        // Add user message
        get().addMessage(sessionId, {
          role: "user",
          content,
        });
        
        set({ isLoading: true, error: null });
        
        try {
          // This will be replaced with actual API call
          await new Promise((resolve) => setTimeout(resolve, 1000));
          
          // Mock AI response
          get().addMessage(sessionId, {
            role: "assistant",
            content: `I've received your message: "${content}". This is a placeholder response from the AI assistant. In a real implementation, this would be a response from the API.`,
          });
          
          set({ isLoading: false });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Failed to send message",
            isLoading: false,
          });
          
          // Add system error message
          get().addMessage(sessionId, {
            role: "system",
            content: "Sorry, there was an error processing your request. Please try again.",
          });
        }
      },
      
      clearMessages: (sessionId) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? { ...session, messages: [], updatedAt: new Date().toISOString() }
              : session
          ),
        }));
      },
      
      clearError: () => set({ error: null }),
    }),
    {
      name: "chat-storage",
      partialize: (state) => ({ 
        sessions: state.sessions, 
        currentSessionId: state.currentSessionId 
      }),
    }
  )
);