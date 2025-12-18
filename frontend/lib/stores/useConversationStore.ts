import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '@/lib/api'

// ─────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────

export interface Message {
    id: string
    role: 'user' | 'assistant' | 'system'
    content: string
    sources?: Array<{ filename: string; content: string }>
    createdAt: string
}

export interface Conversation {
    id: string
    title: string
    mode: 'text' | 'voice'
    createdAt: string
    updatedAt: string | null
    isPinned: boolean
    messageCount: number
}

export interface ConversationDetail extends Conversation {
    summary: string | null
    messages: Message[]
}

// ─────────────────────────────────────────────────────────────────────
// Store State
// ─────────────────────────────────────────────────────────────────────

interface ConversationState {
    // Current conversation
    currentConversationId: string | null
    messages: Message[]
    isLoadingMessages: boolean

    // Conversation list
    conversations: Conversation[]
    isLoadingConversations: boolean
    hasFetchedConversations: boolean

    // Actions - Local State
    setCurrentConversation: (id: string | null) => void
    addMessage: (message: Message) => void
    updateMessage: (id: string, updates: Partial<Message>) => void
    clearMessages: () => void

    // Actions - API
    fetchConversations: () => Promise<void>
    refetchConversations: () => Promise<void>  // Force refresh (bypasses guard)
    createConversation: (title?: string, mode?: 'text' | 'voice') => Promise<string>
    loadConversation: (id: string) => Promise<void>
    deleteConversation: (id: string) => Promise<void>
    updateConversationTitle: (id: string, title: string) => Promise<void>
    togglePinConversation: (id: string) => Promise<void>

    // New Chat
    startNewChat: () => void
    addConversationOptimistic: (id: string, title: string, mode?: 'text' | 'voice') => void
    updateConversationId: (tempId: string, realId: string) => void
}

// ─────────────────────────────────────────────────────────────────────
// Store Implementation
// ─────────────────────────────────────────────────────────────────────

export const useConversationStore = create<ConversationState>()(
    persist(
        (set, get) => ({
            // Initial State
            currentConversationId: null,
            messages: [],
            isLoadingMessages: false,
            conversations: [],
            isLoadingConversations: false,
            hasFetchedConversations: false,

            // ─────────────────────────────────────────────────────────────
            // Local State Actions
            // ─────────────────────────────────────────────────────────────

            setCurrentConversation: (id) => set({ currentConversationId: id }),

            addMessage: (message) => set((state) => ({
                messages: [...state.messages, message]
            })),

            updateMessage: (id, updates) => set((state) => ({
                messages: state.messages.map((msg) =>
                    msg.id === id ? { ...msg, ...updates } : msg
                )
            })),

            clearMessages: () => set({ messages: [], currentConversationId: null }),

            startNewChat: () => {
                set({
                    currentConversationId: null,
                    messages: []
                })
            },

            addConversationOptimistic: (id, title, mode = 'text') => {
                // Instantly add a new conversation to the top of the list (optimistic update)
                const newConversation: Conversation = {
                    id,
                    title,
                    mode,
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString(),
                    isPinned: false,
                    messageCount: 0
                }
                set((state) => ({
                    conversations: [newConversation, ...state.conversations]
                }))
            },

            updateConversationId: (tempId, realId) => {
                // Replace temp ID with real ID from backend
                set((state) => ({
                    conversations: state.conversations.map(c =>
                        c.id === tempId ? { ...c, id: realId } : c
                    ),
                    currentConversationId: state.currentConversationId === tempId ? realId : state.currentConversationId
                }))
            },

            // ─────────────────────────────────────────────────────────────
            // API Actions
            // ─────────────────────────────────────────────────────────────

            fetchConversations: async () => {
                // Prevent duplicate fetches from multiple component instances
                if (get().isLoadingConversations || get().hasFetchedConversations) {
                    return
                }
                set({ isLoadingConversations: true })
                try {
                    // Backend returns snake_case, we need camelCase
                    interface BackendConversation {
                        id: string
                        title: string
                        mode: string
                        created_at: string
                        updated_at: string | null
                        is_pinned: boolean
                        message_count: number
                    }
                    const response = await api.get<BackendConversation[]>('/conversations/')

                    // Transform snake_case to camelCase
                    const conversations: Conversation[] = response.data.map(conv => ({
                        id: conv.id,
                        title: conv.title,
                        mode: conv.mode as 'text' | 'voice',
                        createdAt: conv.created_at,
                        updatedAt: conv.updated_at,
                        isPinned: conv.is_pinned,
                        messageCount: conv.message_count
                    }))

                    set({
                        conversations,
                        isLoadingConversations: false,
                        hasFetchedConversations: true
                    })
                } catch (error) {
                    console.error('Failed to fetch conversations:', error)
                    set({ isLoadingConversations: false, hasFetchedConversations: true })
                }
            },

            refetchConversations: async () => {
                // Force refresh - bypasses the guard for intentional updates
                if (get().isLoadingConversations) return
                console.log('[refetchConversations] Starting fetch...')
                set({ isLoadingConversations: true })
                try {
                    // Backend returns snake_case, we need camelCase
                    interface BackendConversation {
                        id: string
                        title: string
                        mode: string
                        created_at: string
                        updated_at: string | null
                        is_pinned: boolean
                        message_count: number
                    }
                    const response = await api.get<BackendConversation[]>('/conversations/')
                    console.log('[refetchConversations] Raw response:', response.data)

                    // Transform snake_case to camelCase
                    const conversations: Conversation[] = response.data.map(conv => ({
                        id: conv.id,
                        title: conv.title,
                        mode: conv.mode as 'text' | 'voice',
                        createdAt: conv.created_at,
                        updatedAt: conv.updated_at,
                        isPinned: conv.is_pinned,
                        messageCount: conv.message_count
                    }))

                    console.log('[refetchConversations] Transformed:', conversations)
                    set({
                        conversations,
                        isLoadingConversations: false
                    })
                } catch (error) {
                    console.error('[refetchConversations] Failed:', error)
                    set({ isLoadingConversations: false })
                }
            },

            createConversation: async (title = 'New Conversation', mode = 'text') => {
                try {
                    const response = await api.post<Conversation>('/conversations', {
                        title,
                        mode
                    })
                    const newConversation = response.data

                    set((state) => ({
                        conversations: [newConversation, ...state.conversations],
                        currentConversationId: newConversation.id,
                        messages: []
                    }))

                    return newConversation.id
                } catch (error) {
                    console.error('Failed to create conversation:', error)
                    throw error
                }
            },

            loadConversation: async (id) => {
                set({ isLoadingMessages: true })
                try {
                    const response = await api.get<ConversationDetail>(`/conversations/${id}`)
                    const detail = response.data

                    set({
                        currentConversationId: id,
                        messages: detail.messages.map((msg) => ({
                            id: msg.id,
                            role: msg.role as 'user' | 'assistant' | 'system',
                            content: msg.content,
                            sources: msg.sources || [],
                            createdAt: msg.createdAt
                        })),
                        isLoadingMessages: false
                    })
                } catch (error) {
                    console.error('Failed to load conversation:', error)
                    set({ isLoadingMessages: false })
                }
            },

            deleteConversation: async (id) => {
                // Optimistic update - remove from UI immediately
                const { currentConversationId, conversations } = get()
                const previousConversations = conversations

                set((state) => ({
                    conversations: state.conversations.filter((c) => c.id !== id),
                    currentConversationId: currentConversationId === id ? null : currentConversationId,
                    messages: currentConversationId === id ? [] : state.messages
                }))

                try {
                    await api.delete(`/conversations/${id}`)
                } catch (error) {
                    // Rollback on error
                    console.error('Failed to delete conversation:', error)
                    set({ conversations: previousConversations })
                    throw error
                }
            },

            updateConversationTitle: async (id, title) => {
                // Optimistic update - change title immediately
                const previousConversations = get().conversations

                set((state) => ({
                    conversations: state.conversations.map((c) =>
                        c.id === id ? { ...c, title } : c
                    )
                }))

                try {
                    await api.patch(`/conversations/${id}`, { title })
                } catch (error) {
                    // Rollback on error
                    console.error('Failed to update conversation title:', error)
                    set({ conversations: previousConversations })
                    throw error
                }
            },

            togglePinConversation: async (id) => {
                const conversation = get().conversations.find((c) => c.id === id)
                if (!conversation) return

                const newPinnedParam = !conversation.isPinned
                const previousConversations = get().conversations

                // Optimistic update - toggle pin and re-sort immediately
                set((state) => {
                    const updatedConversations = state.conversations.map((c) =>
                        c.id === id ? { ...c, isPinned: newPinnedParam } : c
                    )

                    // Sort: Pinned first, then by date
                    const sortedConversations = [...updatedConversations].sort((a, b) => {
                        if (a.isPinned !== b.isPinned) return a.isPinned ? -1 : 1
                        return new Date(b.updatedAt || b.createdAt).getTime() - new Date(a.updatedAt || a.createdAt).getTime()
                    })

                    return { conversations: sortedConversations }
                })

                try {
                    await api.patch(`/conversations/${id}`, { is_pinned: newPinnedParam })
                } catch (error) {
                    // Rollback on error
                    console.error('Failed to toggle pin:', error)
                    set({ conversations: previousConversations })
                    throw error
                }
            }
        }),
        {
            name: 'samvaad-conversations',
            // Only persist the current conversation ID, not the full message list
            partialize: (state) => ({
                currentConversationId: state.currentConversationId
            })
        }
    )
)
