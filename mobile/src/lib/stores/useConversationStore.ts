import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { api } from "@/lib/api";
import { isValidUUID, sanitizeInput } from "@/lib/utils";

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: Record<string, unknown>[];
  createdAt: string;
}


export interface Conversation {
  id: string;
  title: string;
  mode: "text" | "voice";
  createdAt: string;
  updatedAt: string | null;
  isPinned: boolean;
  messageCount: number;
}

export interface ConversationDetail extends Conversation {
  summary: string | null;
  messages: Message[];
}

interface BackendConversation {
  id: string;
  title: string;
  mode: string;
  created_at: string;
  updated_at: string | null;
  is_pinned: boolean;
  message_count: number;
}

interface BackendMessage {
  id: string;
  role: string;
  content: string;
  sources: Record<string, unknown>[];
  created_at: string;
}

interface BackendConversationDetail {
  id: string;
  title: string;
  summary: string | null;
  created_at: string;
  updated_at: string | null;
  messages: BackendMessage[];
}

const transformConversation = (conv: BackendConversation): Conversation => ({
  id: conv.id,
  title: conv.title,
  mode: conv.mode as "text" | "voice",
  createdAt: conv.created_at,
  updatedAt: conv.updated_at,
  isPinned: conv.is_pinned,
  messageCount: conv.message_count,
});

const transformMessage = (msg: BackendMessage): Message => ({
  id: msg.id,
  role: msg.role as "user" | "assistant" | "system",
  content: msg.content,
  sources: msg.sources || [],
  createdAt: msg.created_at,
});

interface ConversationState {
  currentConversationId: string | null;
  messages: Message[];
  isLoadingMessages: boolean;
  isStreaming: boolean;
  userId: string | null;

  conversations: Conversation[];
  isLoadingConversations: boolean;
  hasFetchedConversations: boolean;

  setCurrentConversation: (id: string | null) => void;
  setIsStreaming: (isStreaming: boolean) => void;
  addMessage: (message: Message, conversationId?: string) => void;
  addMessageToUI: (message: Message) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  clearMessages: () => void;
  truncateMessagesAt: (index: number) => void;

  fetchConversations: (forceRefresh?: boolean) => Promise<void>;
  createConversation: (
    title?: string,
    mode?: "text" | "voice"
  ) => Promise<string>;
  loadConversation: (id: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  updateConversationTitle: (id: string, title: string) => Promise<void>;
  togglePinConversation: (id: string) => Promise<void>;

  startNewChat: () => void;
  addConversationOptimistic: (
    id: string,
    title: string,
    mode?: "text" | "voice"
  ) => void;
  updateConversationId: (tempId: string, realId: string) => void;
  setUserId: (userId: string | null) => void;
  reloadFromBackend: (id: string) => Promise<void>;

  isSelectMode: boolean;
  selectedIds: Set<string>;
  toggleSelectMode: () => void;
  toggleSelection: (id: string) => void;
  selectAll: () => void;
  deselectAll: () => void;
  deleteSelectedConversations: () => Promise<void>;
}

export const useConversationStore = create<ConversationState>()(
  persist(
    (set, get) => ({
      currentConversationId: null,
      messages: [],
      isLoadingMessages: false,
      isStreaming: false,
      userId: null,
      conversations: [],
      isLoadingConversations: false,
      hasFetchedConversations: false,

      isSelectMode: false,
      selectedIds: new Set(),

      setCurrentConversation: (id) => set({ currentConversationId: id }),
      setIsStreaming: (isStreaming) => set({ isStreaming }),
      setUserId: (userId) => set({ userId }),

      addMessageToUI: (message) => {
        if (!message.content || !message.content.trim()) {
          return;
        }

        const state = get();
        const recentMessages = state.messages.slice(-5);
        const isDuplicate = recentMessages.some(
          (m) =>
            m.role === message.role &&
            m.content.trim() === message.content.trim()
        );
        if (isDuplicate) {
          return;
        }

        const safeContent = sanitizeInput(message.content);
        const safeMessage = { ...message, content: safeContent };
        set((state) => ({ messages: [...state.messages, safeMessage] }));
      },

      addMessage: async (message, explicitConversationId) => {
        const state = get();
        if (!state.userId) return;

        const safeContent = sanitizeInput(message.content);
        const safeMessage = { ...message, content: safeContent };

        set({ messages: [...state.messages, safeMessage] });
      },

      updateMessage: (id, updates) =>
        set((state) => ({
          messages: state.messages.map((msg) =>
            msg.id === id ? { ...msg, ...updates } : msg
          ),
        })),

      clearMessages: () => set({ messages: [], currentConversationId: null }),

      truncateMessagesAt: (index) => {
        const state = get();
        const newMessages = state.messages.slice(0, index);
        const keepMessageIds = newMessages.map((m) => m.id);

        set({ messages: newMessages });

        if (state.currentConversationId) {
          api
            .delete(`/conversations/${state.currentConversationId}/messages`, {
              data: { keep_message_ids: keepMessageIds },
            })
            .catch((err) => {
              console.warn("[Store] Failed to truncate backend messages:", err);
            });
        }
      },

      startNewChat: () => {
        set({
          currentConversationId: null,
          messages: [],
        });
      },

      addConversationOptimistic: (id, title, mode = "text") => {
        const state = get();
        if (state.conversations.some((c) => c.id === id)) {
          return;
        }

        const newConversation: Conversation = {
          id,
          title,
          mode,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          isPinned: false,
          messageCount: 0,
        };
        set((state) => ({
          conversations: [newConversation, ...state.conversations],
        }));
      },

      updateConversationId: (tempId: string, realId: string) => {
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === tempId ? { ...c, id: realId } : c
          ),
          currentConversationId:
            state.currentConversationId === tempId
              ? realId
              : state.currentConversationId,
        }));
      },

      toggleSelectMode: () =>
        set((state) => ({
          isSelectMode: !state.isSelectMode,
          selectedIds: new Set(),
        })),

      toggleSelection: (id) =>
        set((state) => {
          const newSelected = new Set(state.selectedIds);
          if (newSelected.has(id)) {
            newSelected.delete(id);
          } else {
            newSelected.add(id);
          }
          return { selectedIds: newSelected };
        }),

      selectAll: () =>
        set((state) => ({
          selectedIds: new Set(state.conversations.map((c) => c.id)),
        })),

      deselectAll: () => set({ selectedIds: new Set() }),

      deleteSelectedConversations: async () => {
        const { selectedIds, conversations } = get();
        if (selectedIds.size === 0) return;

        const idsToDelete = Array.from(selectedIds);
        const previousConversations = conversations;

        set((state) => ({
          conversations: state.conversations.filter(
            (c) => !selectedIds.has(c.id)
          ),
          selectedIds: new Set(),
          isSelectMode: false,
          currentConversationId:
            state.currentConversationId &&
            selectedIds.has(state.currentConversationId)
              ? null
              : state.currentConversationId,
        }));

        try {
          await api.delete("/conversations/batch", {
            data: idsToDelete,
          });
        } catch (error) {
          console.error("Failed to bulk delete:", error);
          set({ conversations: previousConversations });
        }
      },

      fetchConversations: async (forceRefresh = false) => {
        if (get().isLoadingConversations) return;
        if (!forceRefresh && get().hasFetchedConversations) return;

        set({ isLoadingConversations: true });

        try {
          const response =
            await api.get<BackendConversation[]>("/conversations/");
          const conversations = response.data.map(transformConversation);

          set({
            conversations,
            isLoadingConversations: false,
            hasFetchedConversations: true,
          });
        } catch (error) {
          console.error("Failed to fetch conversations:", error);
          set({
            isLoadingConversations: false,
            hasFetchedConversations: true,
          });
        }
      },

      createConversation: async (title = "New Conversation", mode = "text") => {
        try {
          const response = await api.post<Conversation>("/conversations", {
            title,
            mode,
          });
          const newConversation = response.data;

          set((state) => ({
            conversations: [newConversation, ...state.conversations],
            currentConversationId: newConversation.id,
            messages: [],
          }));

          return newConversation.id;
        } catch (error) {
          console.error("Failed to create conversation:", error);
          throw error;
        }
      },

      loadConversation: async (id) => {
        if (!isValidUUID(id)) {
          console.error("Invalid conversation ID format");
          return;
        }

        const state = get();
        if (state.isLoadingMessages) return;

        set({ isLoadingMessages: true });

        try {
          const response = await api.get<BackendConversationDetail>(
            `/conversations/${id}`
          );
          const detail = response.data;

          set({
            currentConversationId: id,
            messages: detail.messages.map(transformMessage),
            isLoadingMessages: false,
          });
        } catch (error) {
          console.error("Failed to load conversation:", error);
          set({ isLoadingMessages: false });
        }
      },

      reloadFromBackend: async (id) => {
        if (!isValidUUID(id)) {
          console.error("Invalid conversation ID format");
          return;
        }

        set({ messages: [], isLoadingMessages: true });

        try {
          const response = await api.get<BackendConversationDetail>(
            `/conversations/${id}`
          );
          const detail = response.data;

          set({
            currentConversationId: id,
            messages: detail.messages.map(transformMessage),
            isLoadingMessages: false,
          });
        } catch (error) {
          console.error("Failed to reload conversation:", error);
          set({ isLoadingMessages: false });
        }
      },

      deleteConversation: async (id) => {
        const { currentConversationId, conversations } = get();
        const previousConversations = conversations;

        set((state) => ({
          conversations: state.conversations.filter((c) => c.id !== id),
          currentConversationId:
            currentConversationId === id ? null : currentConversationId,
          messages: currentConversationId === id ? [] : state.messages,
        }));

        try {
          await api.delete(`/conversations/${id}`);
        } catch (error) {
          console.error("Failed to delete conversation:", error);
          set({ conversations: previousConversations });
          throw error;
        }
      },

      updateConversationTitle: async (id, title) => {
        const previousConversations = get().conversations;

        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === id ? { ...c, title } : c
          ),
        }));

        try {
          await api.patch(`/conversations/${id}`, { title });
        } catch (error) {
          console.error("Failed to update conversation title:", error);
          set({ conversations: previousConversations });
          throw error;
        }
      },

      togglePinConversation: async (id) => {
        const conversation = get().conversations.find((c) => c.id === id);
        if (!conversation) return;

        const newPinnedParam = !conversation.isPinned;
        const previousConversations = get().conversations;

        set((state) => {
          const updatedConversations = state.conversations.map((c) =>
            c.id === id ? { ...c, isPinned: newPinnedParam } : c
          );

          const sortedConversations = [...updatedConversations].sort((a, b) => {
            if (a.isPinned !== b.isPinned) return a.isPinned ? -1 : 1;
            return (
              new Date(b.updatedAt || b.createdAt).getTime() -
              new Date(a.updatedAt || a.createdAt).getTime()
            );
          });

          return { conversations: sortedConversations };
        });

        try {
          await api.patch(`/conversations/${id}`, {
            is_pinned: newPinnedParam,
          });
        } catch (error) {
          console.error("Failed to toggle pin:", error);
          set({ conversations: previousConversations });
          throw error;
        }
      },
    }),
    {
      name: "samvaad-conversations",
      storage: createJSONStorage(() => AsyncStorage),
      partialize: () => ({}),
    }
  )
);
