import { create } from 'zustand'

export interface SourceItem {
  id: number | string
  name: string
  type: string
  size: string
  uploadedAt: string
  status: 'uploading' | 'synced' | 'error'
  contentHash?: string // For content-based deduplication
}

export interface DuplicateItem {
  file: File
  match: {
    name: string
    id: string | number
  }
}

interface UIState {
  mode: 'text' | 'voice'
  isSidebarOpen: boolean
  hasInteracted: boolean
  setMode: (mode: 'text' | 'voice') => void
  setHasInteracted: (hasInteracted: boolean) => void
  toggleSidebar: () => void

  // Sources Panel
  isSourcesPanelOpen: boolean
  toggleSourcesPanel: () => void
  setSourcesPanelOpen: (isOpen: boolean) => void

  // Sources Data
  sources: SourceItem[]
  setSources: (sources: SourceItem[]) => void
  addSource: (source: SourceItem) => void
  removeSource: (id: number | string) => void
  updateSourceStatus: (id: number | string, status: 'uploading' | 'synced' | 'error') => void
  updateSource: (id: number | string, updates: Partial<SourceItem>) => void

  // Fetch State
  hasFetchedSources: boolean
  setHasFetchedSources: (hasFetched: boolean) => void

  // Duplicate Management
  pendingDuplicates: DuplicateItem[]
  showDuplicateModal: boolean
  setPendingDuplicates: (files: DuplicateItem[]) => void
  setShowDuplicateModal: (show: boolean) => void
}

export const useUIStore = create<UIState>((set) => ({
  mode: 'text',
  isSidebarOpen: false,
  hasInteracted: false,
  setMode: (mode) => set({ mode }),
  setHasInteracted: (hasInteracted) => set({ hasInteracted }),
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),

  // Sources Panel
  isSourcesPanelOpen: false,
  toggleSourcesPanel: () => set((state) => ({ isSourcesPanelOpen: !state.isSourcesPanelOpen })),
  setSourcesPanelOpen: (isOpen) => set({ isSourcesPanelOpen: isOpen }),

  // Sources Data
  sources: [],
  setSources: (sources) => set({ sources }),
  addSource: (source) => set((state) => ({ sources: [source, ...state.sources] })),
  removeSource: (id) => set((state) => ({ sources: state.sources.filter((s) => s.id !== id) })),
  updateSourceStatus: (id, status) => set((state) => ({
    sources: state.sources.map((s) => s.id === id ? { ...s, status } : s)
  })),
  updateSource: (id, updates) => set((state) => ({
    sources: state.sources.map((s) => s.id === id ? { ...s, ...updates } : s)
  })),

  // Fetch State
  hasFetchedSources: false,
  setHasFetchedSources: (hasFetched) => set({ hasFetchedSources: hasFetched }),

  // Duplicate Management
  pendingDuplicates: [],
  showDuplicateModal: false,
  setPendingDuplicates: (files) => set({ pendingDuplicates: files }),
  setShowDuplicateModal: (show) => set({ showDuplicateModal: show }),
}))
